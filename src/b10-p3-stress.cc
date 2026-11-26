// COMOV B10 - P3: isolated three-stressor experiments; P2 stays unchanged.
// Target: ns-3.48. Pilot: one shared topology, two application policies.
// All 1000-byte UDP payloads contain a 16-byte [sequence,generation_ns] header.

#include "ns3/core-module.h"
#include "ns3/applications-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/propagation-module.h"
#include "ns3/wifi-module.h"

#include <algorithm>
#include <array>
#include <deque>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <string>

using namespace ns3;

namespace
{
constexpr double kSpeedOfLight = 299792458.0;
constexpr double kPi = 3.14159265358979323846;
constexpr uint32_t kPayloadBytes = 1000;
constexpr uint32_t kHeaderBytes = 16;
constexpr uint32_t kPacketsPerSecond = 100;
constexpr uint32_t kPacketCount = 12000;
constexpr double kGenerationStartS = 10.0;
constexpr double kStopAtS = 70.0;
constexpr double kObserveUntilS = 200.0;
constexpr double kDeadlineS = 60.0;
constexpr uint16_t kUdpPort = 9010;
constexpr uint16_t kBackgroundUdpPort = 9011;

struct BufferedMessage
{
    uint64_t sequence{0};
    int64_t generatedNs{0};
};

struct Pilot
{
    Ptr<ConstantVelocityMobilityModel> bus;
    Ptr<ConstantPositionMobilityModel> ap;
    Ptr<StaWifiMac> mac;
    Ptr<LogDistancePropagationLossModel> loss;
    Ptr<LogDistancePropagationLossModel> monitorLoss;
    Ptr<Socket> sender;
    Ipv4Address apIpv4;
    double speed{5.0};
    double stopSeconds{10.0};
    double apX{0.0};
    double txDbm{20.0};
    std::string scenario{"reference"};
    uint64_t backgroundRateBps{2000000};
    uint64_t backgroundRxPackets{0};
    uint64_t backgroundRxBytes{0};
    uint32_t generated{0};
    uint32_t dropNoAssociation{0};
    uint32_t socketRejected{0};
    uint32_t socketAccepted{0};
    uint32_t uniqueReceived{0};
    uint32_t duplicateReceived{0};
    uint32_t malformedReceived{0};
    uint32_t receivedOnTime{0};
    uint32_t receivedLate{0};
    uint32_t associationEvents{0};
    uint32_t disassociationEvents{0};
    uint32_t ignoredAssocCallbacks{0};
    uint32_t ignoredDeassocCallbacks{0};
    bool associationOpen{false};
    double associationStartS{0.0};
    double totalAssociatedS{0.0};
    std::set<uint64_t> uniqueIds;
    std::deque<BufferedMessage> queue;
    uint64_t bufferedBytes{0};
    uint64_t maximumBufferedBytes{0};
    uint64_t bufferLimitBytes{4000000};
    uint32_t enqueued{0};
    uint32_t overflowDropNewest{0};
    uint32_t expiredBeforeSend{0};
    uint32_t bufferSendAttempts{0};
    bool flushScheduled{false};
    int64_t lastSocketAttemptNs{-1};
    double pacingMs{2.0};
    std::string policy{"fifo"};
    std::ofstream bufferEventsCsv;
    std::ofstream sentCsv;
    std::ofstream generatedCsv;
    std::ofstream receivedCsv;
    std::ofstream associationCsv;
    std::ofstream associationRawCsv;
    std::ofstream mobilityCsv;
} g;

double
Distance3d()
{
    auto ap = g.ap->GetPosition();
    auto bus = g.bus->GetPosition();
    return std::sqrt(std::pow(ap.x - bus.x, 2) +
                     std::pow(ap.y - bus.y, 2) +
                     std::pow(ap.z - bus.z, 2));
}

void
WriteUInt64(uint8_t* out, uint64_t value)
{
    for (int i = 7; i >= 0; --i)
    {
        out[i] = static_cast<uint8_t>(value & 0xff);
        value >>= 8;
    }
}

uint64_t
ReadUInt64(const uint8_t* bytes)
{
    uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i)
    {
        value = (value << 8) | static_cast<uint64_t>(bytes[i]);
    }
    return value;
}

void ScheduleFlush();

// The P3 fading scenario may generate DeAssoc callbacks without a preceding
// successful Assoc trace. Preserve every raw callback for diagnosis, while
// writing only proper association state transitions to association.csv.
void
LogRawAssociation(const char* type, Mac48Address apMac)
{
    g.associationRawCsv << Simulator::Now().GetSeconds() << ',' << type << ','
                        << (g.associationOpen ? 1 : 0) << ','
                        << (g.mac->IsAssociated() ? 1 : 0) << ','
                        << g.bus->GetPosition().x << ',' << Distance3d()
                        << ',' << apMac << '\n';
}

void
OnAssociation(Mac48Address apMac)
{
    LogRawAssociation("assoc_cb", apMac);
    if (g.associationOpen)
    {
        ++g.ignoredAssocCallbacks;
        return;
    }
    const double now = Simulator::Now().GetSeconds();
    ++g.associationEvents;
    g.associationOpen = true;
    g.associationStartS = now;
    g.associationCsv << now << ",assoc," << apMac << ','
                     << g.bus->GetPosition().x << ',' << Distance3d() << '\n';
    ScheduleFlush();
}

void
OnDisassociation(Mac48Address apMac)
{
    LogRawAssociation("deassoc_cb", apMac);
    if (!g.associationOpen)
    {
        ++g.ignoredDeassocCallbacks;
        return;
    }
    const double now = Simulator::Now().GetSeconds();
    ++g.disassociationEvents;
    g.totalAssociatedS += now - g.associationStartS;
    g.associationOpen = false;
    g.associationCsv << now << ",deassoc," << apMac << ','
                     << g.bus->GetPosition().x << ',' << Distance3d() << '\n';
}

void
RecordMobility()
{
    const auto pos = g.bus->GetPosition();
    const auto velocity = g.bus->GetVelocity();
    const bool associated = g.mac->IsAssociated();
    // Never consume fading RNG for telemetry at 4Hz. Monitor only log-distance.
    const double predictedRxDbm = g.monitorLoss->CalcRxPower(g.txDbm, g.ap, g.bus);
    g.mobilityCsv << Simulator::Now().GetSeconds() << ',' << pos.x << ','
                  << velocity.x << ',' << Distance3d() << ','
                  << (associated ? 1 : 0) << ',' << predictedRxDbm << '\n';
}

void
StopBus()
{
    g.bus->SetVelocity(Vector(0.0, 0.0, 0.0));
}

void
ResumeBus()
{
    g.bus->SetVelocity(Vector(g.speed, 0.0, 0.0));
}

void
LogBufferEvent(uint64_t sequence, const char* event, double ageS, int32_t sendReturn)
{
    if (g.policy != "fifo")
    {
        return;
    }
    g.bufferEventsCsv << Simulator::Now().GetSeconds() << ',' << sequence << ','
                      << event << ',' << g.queue.size() << ',' << g.bufferedBytes
                      << ',' << (g.mac->IsAssociated() ? 1 : 0)
                      << ',' << ageS << ',';
    if (sendReturn != -9999)
    {
        g.bufferEventsCsv << sendReturn;
    }
    g.bufferEventsCsv << '\n';
}

void
PurgeExpired()
{
    if (g.policy != "fifo")
    {
        return;
    }
    const int64_t nowNs = Simulator::Now().GetNanoSeconds();
    const int64_t deadlineNs = static_cast<int64_t>(kDeadlineS * 1e9);
    while (!g.queue.empty() &&
           nowNs - g.queue.front().generatedNs >= deadlineNs)
    {
        const BufferedMessage old = g.queue.front();
        g.queue.pop_front();
        g.bufferedBytes -= kPayloadBytes;
        ++g.expiredBeforeSend;
        LogBufferEvent(old.sequence, "expired", (nowNs - old.generatedNs) / 1e9, -9999);
    }
}

// Called at the exact deadline of each buffered message, even if no Wi-Fi
// association exists. This means messages cannot occupy memory after expiry.
void
ExpireAtDeadline()
{
    PurgeExpired();
}

void
FlushOne();

void
ScheduleFlush()
{
    if (g.policy != "fifo" || g.flushScheduled || !g.mac->IsAssociated() ||
        g.queue.empty())
    {
        return;
    }
    // Enforce pacing even when the FIFO becomes empty between two generations.
    // This avoids a transient burst shorter than pacingMs after an empty queue.
    const int64_t nowNs = Simulator::Now().GetNanoSeconds();
    const int64_t intervalNs = static_cast<int64_t>(g.pacingMs * 1e6);
    const int64_t earliestNs = (g.lastSocketAttemptNs < 0) ?
        nowNs : (g.lastSocketAttemptNs + intervalNs);
    const int64_t delayNs = std::max<int64_t>(0, earliestNs - nowNs);
    g.flushScheduled = true;
    Simulator::Schedule(NanoSeconds(delayNs), &FlushOne);
}

void
FlushOne()
{
    g.flushScheduled = false;
    PurgeExpired();
    if (g.policy != "fifo" || !g.mac->IsAssociated() || g.queue.empty())
    {
        return;
    }
    // Strict FIFO: the queue is ordered by generation time. A packet is
    // removed when submitted to UDP, NOT when received by the AP.
    const BufferedMessage msg = g.queue.front();
    g.queue.pop_front();
    g.bufferedBytes -= kPayloadBytes;
    const int64_t nowNs = Simulator::Now().GetNanoSeconds();
    const double ageS = (nowNs - msg.generatedNs) / 1e9;

    std::array<uint8_t, kPayloadBytes> payload{};
    WriteUInt64(payload.data(), msg.sequence);
    WriteUInt64(payload.data() + 8, static_cast<uint64_t>(msg.generatedNs));
    const Ptr<Packet> packet = Create<Packet>(payload.data(), kPayloadBytes);
    const int n = g.sender->SendTo(
        packet, 0, InetSocketAddress(g.apIpv4, kUdpPort));
    g.lastSocketAttemptNs = nowNs;

    ++g.bufferSendAttempts;
    if (n == static_cast<int>(kPayloadBytes))
    {
        ++g.socketAccepted;
        LogBufferEvent(msg.sequence, "send_accepted", ageS, n);
    }
    else
    {
        ++g.socketRejected;
        LogBufferEvent(msg.sequence, "send_rejected", ageS, n);
    }
    g.sentCsv << msg.sequence << ',' << (msg.generatedNs / 1e9) << ','
              << Simulator::Now().GetSeconds() << ',' << ageS << ',' << n
              << ",fifo\n";

    if (g.mac->IsAssociated() && !g.queue.empty())
    {
        // Send at most one application datagram per pacing interval.
        // Socket acceptance still does NOT guarantee MAC/PHY delivery.
        g.flushScheduled = true;
        Simulator::Schedule(Seconds(g.pacingMs / 1000.0), &FlushOne);
    }
}

void
Generate(uint64_t sequence, Ipv4Address apAddress)
{
    const double nowS = Simulator::Now().GetSeconds();
    const int64_t genNs = Simulator::Now().GetNanoSeconds();
    const bool associated = g.mac->IsAssociated();
    const double x = g.bus->GetPosition().x;
    ++g.generated;

    if (g.policy == "fifo")
    {
        PurgeExpired();
        if (g.bufferedBytes + kPayloadBytes > g.bufferLimitBytes)
        {
            ++g.overflowDropNewest;
            g.generatedCsv << sequence << ',' << nowS << ',' << x << ','
                           << Distance3d() << ',' << (associated ? 1 : 0)
                           << ",0,,buffer_full\n";
            LogBufferEvent(sequence, "drop_newest", 0.0, -9999);
            return;
        }

        // Buffer is logical application payload: 1000 bytes/message.
        // We only store ID+time as compact metadata; packet contents are
        // deterministically reconstructed when submitted to UDP.
        g.queue.push_back({sequence, genNs});
        g.bufferedBytes += kPayloadBytes;
        g.maximumBufferedBytes = std::max(g.maximumBufferedBytes, g.bufferedBytes);
        ++g.enqueued;
        g.generatedCsv << sequence << ',' << nowS << ',' << x << ','
                       << Distance3d() << ',' << (associated ? 1 : 0)
                       << ",0,,enqueued\n";
        LogBufferEvent(sequence, "enqueued", 0.0, -9999);
        Simulator::Schedule(Seconds(kDeadlineS), &ExpireAtDeadline);
        ScheduleFlush();
        return;
    }

    // Strict immediate policy: no application buffer; do not submit UDP
    // while the station reports no association with the AP.
    if (!associated)
    {
        ++g.dropNoAssociation;
        g.generatedCsv << sequence << ',' << nowS << ',' << x << ','
                       << Distance3d() << ",0,0,,no_association\n";
        return;
    }

    std::array<uint8_t, kPayloadBytes> payload{};
    WriteUInt64(payload.data(), sequence);
    WriteUInt64(payload.data() + 8, static_cast<uint64_t>(genNs));
    const Ptr<Packet> packet = Create<Packet>(payload.data(), kPayloadBytes);
    const int n = g.sender->SendTo(packet, 0, InetSocketAddress(apAddress, kUdpPort));
    if (n != static_cast<int>(kPayloadBytes))
    {
        ++g.socketRejected;
        g.generatedCsv << sequence << ',' << nowS << ',' << x << ','
                       << Distance3d() << ",1,1," << n << ",socket_rejected\n";
    }
    else
    {
        ++g.socketAccepted;
        g.generatedCsv << sequence << ',' << nowS << ',' << x << ','
                       << Distance3d() << ",1,1," << n << ",\n";
    }
    g.sentCsv << sequence << ',' << nowS << ',' << nowS << ",0.0,"
              << n << ",immediate\n";
    // SendTo return == 1000 means acceptance at the UDP socket, not delivery.
}

void
OnBackgroundDatagram(Ptr<Socket> receiver)
{
    Address from;
    while (auto packet = receiver->RecvFrom(from))
    {
        ++g.backgroundRxPackets;
        g.backgroundRxBytes += packet->GetSize();
    }
}

void
OnDatagram(Ptr<Socket> receiver)
{
    Address from;
    while (auto packet = receiver->RecvFrom(from))
    {
        const double nowS = Simulator::Now().GetSeconds();
        if (packet->GetSize() != kPayloadBytes)
        {
            ++g.malformedReceived;
            continue;
        }

        std::array<uint8_t, kPayloadBytes> bytes{};
        const uint32_t copied = packet->CopyData(bytes.data(), kPayloadBytes);
        if (copied != kPayloadBytes)
        {
            ++g.malformedReceived;
            continue;
        }

        const uint64_t sequence = ReadUInt64(bytes.data());
        const uint64_t genNs = ReadUInt64(bytes.data() + 8);
        const double tGen = static_cast<double>(genNs) / 1e9;
        if (sequence >= kPacketCount || genNs > static_cast<uint64_t>(Simulator::Now().GetNanoSeconds()))
        {
            ++g.malformedReceived;
            continue;
        }

        const bool duplicate = !g.uniqueIds.insert(sequence).second;
        const double delayS = (static_cast<double>(
            Simulator::Now().GetNanoSeconds() - static_cast<int64_t>(genNs))) / 1e9;
        const bool onTime = delayS <= kDeadlineS;
        if (duplicate)
        {
            ++g.duplicateReceived;
        }
        else
        {
            ++g.uniqueReceived;
            if (onTime)
            {
                ++g.receivedOnTime;
            }
            else
            {
                ++g.receivedLate;
            }
        }
        g.receivedCsv << sequence << ',' << tGen << ',' << nowS << ','
                      << delayS << ',' << (onTime ? 1 : 0) << ','
                      << (duplicate ? 1 : 0) << ','
                      << (g.mac->IsAssociated() ? 1 : 0) << '\n';
    }
}

void
OpenCsv(std::ofstream& file, const std::string& filename, const std::string& columns)
{
    file.open(filename, std::ios::out | std::ios::trunc);
    NS_ABORT_MSG_IF(!file.is_open(), "Cannot write " << filename);
    file << std::fixed << std::setprecision(9) << columns << '\n';
}
} // namespace

int
main(int argc, char** argv)
{
    std::string prefix{"p2"};
    std::string policy{"fifo"};
    double pacingMs{2.0};
    uint64_t bufferLimitBytes{4000000};
    uint32_t seed{1};
    uint64_t run{1};
    double speed{5.0};
    double stopSeconds{10.0};
    double apX{0.0};
    double exponent{3.0};
    double txDbm{20.0};
    std::string scenario{"reference"};
    uint64_t backgroundRateBps{2000000};

    CommandLine cmd(__FILE__);
    cmd.AddValue("prefix", "Output prefix, existing parent directory required", prefix);
    cmd.AddValue("scenario", "reference|fading|contention", scenario);
    cmd.AddValue("backgroundRateBps", "Competing STA offered rate in contention mode", backgroundRateBps);
    cmd.AddValue("policy", "immediate or fifo", policy);
    cmd.AddValue("pacingMs", "FIFO inter-submission interval [ms]", pacingMs);
    cmd.AddValue("bufferBytes", "FIFO capacity in application bytes", bufferLimitBytes);
    cmd.AddValue("speed", "Bus approach/departure speed [m/s]", speed);
    cmd.AddValue("stop", "Stop duration [s]", stopSeconds);
    cmd.AddValue("apX", "AP x-position [m], 0 in reference scenario", apX);
    cmd.AddValue("exponent", "Log-distance path-loss exponent", exponent);
    cmd.AddValue("txDbm", "Wi-Fi transmitter power [dBm]", txDbm);
    cmd.AddValue("seed", "RNG seed", seed);
    cmd.AddValue("run", "RNG run number", run);
    cmd.Parse(argc, argv);

    NS_ABORT_MSG_IF((speed != 5.0 && speed != 15.0) ||
                    (stopSeconds != 0.0 && stopSeconds != 10.0 && stopSeconds != 30.0),
                    "B10 P1: speed must be 5 or 15, stop must be 0/10/30");
    NS_ABORT_MSG_IF(exponent <= 0.0 || run == 0, "Invalid exponent or RNG run");
    NS_ABORT_MSG_IF(policy != "fifo" && policy != "immediate",
                    "--policy must be fifo or immediate");
    NS_ABORT_MSG_IF(scenario != "reference" && scenario != "fading" && scenario != "contention",
                    "--scenario must be reference/fading/contention");
    NS_ABORT_MSG_IF(backgroundRateBps < 1000 || backgroundRateBps > 10000000,
                    "Invalid competing traffic rate");
    NS_ABORT_MSG_IF(pacingMs < 0.1 || pacingMs > 100.0 ||
                    bufferLimitBytes < kPayloadBytes ||
                    bufferLimitBytes % kPayloadBytes != 0,
                    "Invalid pacingMs or bufferBytes (multiple of 1000 required)");

    g.speed = speed;
    g.stopSeconds = stopSeconds;
    g.apX = apX;
    g.txDbm = txDbm;
    g.scenario = scenario;
    g.backgroundRateBps = backgroundRateBps;
    g.policy = policy;
    g.pacingMs = pacingMs;
    g.bufferLimitBytes = bufferLimitBytes;
    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(run);

    OpenCsv(g.generatedCsv, prefix + "_generated.csv",
            "seq,t_gen_s,bus_x_m,distance_ap_m,associated_at_generation,"
            "attempted_socket_send,send_return,drop_reason");
    OpenCsv(g.receivedCsv, prefix + "_received.csv",
            "seq,t_gen_s,t_rx_s,delay_s,on_time,duplicate,associated_at_reception");
    OpenCsv(g.associationCsv, prefix + "_association.csv",
            "t_s,event,ap_mac,bus_x_m,distance_ap_m");
    OpenCsv(g.associationRawCsv, prefix + "_association_raw.csv",
            "t_s,callback,already_open,sta_is_associated,bus_x_m,distance_ap_m,ap_mac");
    OpenCsv(g.mobilityCsv, prefix + "_mobility.csv",
            "t_s,bus_x_m,bus_velocity_mps,distance_ap_m,associated,pr_model_dbm");
    OpenCsv(g.bufferEventsCsv, prefix + "_buffer.csv",
            "t_s,seq,event,queued_messages,queued_bytes,associated,age_s,send_return");
    OpenCsv(g.sentCsv, prefix + "_sent.csv",
            "seq,t_gen_s,t_socket_s,age_at_send_s,send_return,policy");

    NodeContainer apNode;
    NodeContainer busNode;
    apNode.Create(1);
    busNode.Create(1);

    MobilityHelper apMob;
    apMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    apMob.Install(apNode);
    g.ap = apNode.Get(0)->GetObject<ConstantPositionMobilityModel>();
    g.ap->SetPosition(Vector(apX, 0.0, 4.0));

    MobilityHelper busMob;
    busMob.SetMobilityModel("ns3::ConstantVelocityMobilityModel");
    busMob.Install(busNode);
    g.bus = busNode.Get(0)->GetObject<ConstantVelocityMobilityModel>();
    // Starting at -70*v means x=0 at t=70 s, regardless of speed.
    g.bus->SetPosition(Vector(-kStopAtS * speed, 0.0, 2.5));
    g.bus->SetVelocity(Vector(speed, 0.0, 0.0));
    if (stopSeconds > 0.0)
    {
        Simulator::Schedule(Seconds(kStopAtS), &StopBus);
        Simulator::Schedule(Seconds(kStopAtS + stopSeconds), &ResumeBus);
    }

    const double frequencyHz = 2.412e9;
    const double referenceLoss = 20.0 * std::log10(
        (4.0 * kPi * frequencyHz) / kSpeedOfLight);

    g.loss = CreateObject<LogDistancePropagationLossModel>();
    g.loss->SetAttribute("Exponent", DoubleValue(exponent));
    g.loss->SetAttribute("ReferenceDistance", DoubleValue(1.0));
    g.loss->SetAttribute("ReferenceLoss", DoubleValue(referenceLoss));

    // Separate deterministic monitor; sampled traces must not consume
    // any random fading draws that change simulated packet delivery.
    g.monitorLoss = CreateObject<LogDistancePropagationLossModel>();
    g.monitorLoss->SetAttribute("Exponent", DoubleValue(exponent));
    g.monitorLoss->SetAttribute("ReferenceDistance", DoubleValue(1.0));
    g.monitorLoss->SetAttribute("ReferenceLoss", DoubleValue(referenceLoss));
    if (scenario == "fading")
    {
        // Rayleigh small-scale fading: Nakagami m=1 at all distances.
        // This is a declared stress test, not a calibrated real street.
        auto fading = CreateObject<NakagamiPropagationLossModel>();
        fading->SetAttribute("m0", DoubleValue(1.0));
        fading->SetAttribute("m1", DoubleValue(1.0));
        fading->SetAttribute("m2", DoubleValue(1.0));
        g.loss->SetNext(fading);
    }

    auto channel = CreateObject<YansWifiChannel>();
    channel->SetPropagationDelayModel(CreateObject<ConstantSpeedPropagationDelayModel>());
    channel->SetPropagationLossModel(g.loss);

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211g);
    // IEEE 802.11g at 2.4 GHz uses ERP-OFDM, not legacy OFDM.
    // OfdmRate6Mbps is a 5 GHz OFDM mode and causes a fatal error once
    // unicast data are transmitted in ns-3.48 (WifiTxVector::IsValid).
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                 "DataMode", StringValue("ErpOfdmRate6Mbps"),
                                 "ControlMode", StringValue("ErpOfdmRate6Mbps"));

    YansWifiPhyHelper phy;
    phy.SetChannel(channel);
    phy.Set("TxPowerStart", DoubleValue(txDbm));
    phy.Set("TxPowerEnd", DoubleValue(txDbm));
    phy.Set("TxPowerLevels", UintegerValue(1));
    phy.Set("TxGain", DoubleValue(0.0));
    phy.Set("RxGain", DoubleValue(0.0));
    phy.Set("ChannelSettings", StringValue("{1, 20, BAND_2_4GHZ, 0}"));

    WifiMacHelper mac;
    Ssid ssid{"COMOV-B10-P1"};
    mac.SetType("ns3::ApWifiMac", "Ssid", SsidValue(ssid));
    NetDeviceContainer apDevices = wifi.Install(phy, mac, apNode);
    mac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(ssid),
                "ActiveProbing", BooleanValue(true));
    NetDeviceContainer busDevices = wifi.Install(phy, mac, busNode);

    // Independent Wi-Fi STA. It competes for the SAME AP and channel.
    NodeContainer backgroundNode;
    NetDeviceContainer backgroundDevices;
    if (scenario == "contention")
    {
        backgroundNode.Create(1);
        MobilityHelper backgroundMob;
        backgroundMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
        backgroundMob.Install(backgroundNode);
        backgroundNode.Get(0)->GetObject<ConstantPositionMobilityModel>()
            ->SetPosition(Vector(10.0, 0.0, 2.5));
        backgroundDevices = wifi.Install(phy, mac, backgroundNode);
    }

    // Capture management frames, ARP and UDP in the fading pilot.
    // Packet capture does not replace the per-message CSV accounting.
    if (scenario == "fading")
    {
        phy.EnablePcap(prefix + "_pcap_ap", apDevices);
        phy.EnablePcap(prefix + "_pcap_bus", busDevices);
    }

    g.mac = DynamicCast<StaWifiMac>(DynamicCast<WifiNetDevice>(
        busDevices.Get(0))->GetMac());
    NS_ABORT_MSG_IF(!g.mac, "Cannot access StaWifiMac for association trace");
    NS_ABORT_MSG_IF(!g.mac->TraceConnectWithoutContext(
                        "Assoc", MakeCallback(&OnAssociation)),
                    "Failed to connect Assoc trace");
    NS_ABORT_MSG_IF(!g.mac->TraceConnectWithoutContext(
                        "DeAssoc", MakeCallback(&OnDisassociation)),
                    "Failed to connect DeAssoc trace");

    InternetStackHelper internet;
    internet.Install(apNode);
    internet.Install(busNode);
    if (scenario == "contention")
    {
        internet.Install(backgroundNode);
    }
    Ipv4AddressHelper addresses;
    addresses.SetBase("10.8.0.0", "255.255.255.0");
    NetDeviceContainer wifiDevices;
    wifiDevices.Add(apDevices);
    wifiDevices.Add(busDevices);
    if (scenario == "contention")
    {
        wifiDevices.Add(backgroundDevices);
    }
    const Ipv4InterfaceContainer interfaces = addresses.Assign(wifiDevices);
    const Ipv4Address apAddress = interfaces.GetAddress(0);
    g.apIpv4 = apAddress;

    Ptr<Socket> receiver = Socket::CreateSocket(apNode.Get(0),
                                                UdpSocketFactory::GetTypeId());
    NS_ABORT_MSG_IF(receiver->Bind(InetSocketAddress(Ipv4Address::GetAny(),
                                                   kUdpPort)) != 0,
                    "AP UDP receiver bind failed");
    receiver->SetRecvCallback(MakeCallback(&OnDatagram));

    if (scenario == "contention")
    {
        Ptr<Socket> backgroundSink =
            Socket::CreateSocket(apNode.Get(0), UdpSocketFactory::GetTypeId());
        NS_ABORT_MSG_IF(
            backgroundSink->Bind(InetSocketAddress(
                Ipv4Address::GetAny(), kBackgroundUdpPort)) != 0,
            "Background UDP sink bind failed");
        backgroundSink->SetRecvCallback(MakeCallback(&OnBackgroundDatagram));

        OnOffHelper backgroundTraffic(
            "ns3::UdpSocketFactory",
            InetSocketAddress(apAddress, kBackgroundUdpPort));
        backgroundTraffic.SetConstantRate(DataRate(backgroundRateBps), kPayloadBytes);
        auto apps = backgroundTraffic.Install(backgroundNode);
        apps.Start(Seconds(5.0));
        apps.Stop(Seconds(135.0));
    }

    g.sender = Socket::CreateSocket(busNode.Get(0), UdpSocketFactory::GetTypeId());
    NS_ABORT_MSG_IF(g.sender->Bind() != 0, "Bus UDP sender bind failed");

    for (uint32_t i = 0; i < kPacketCount; ++i)
    {
        // Absolute scheduled times, not iterative addition of 10 ms.
        const double tS = kGenerationStartS + static_cast<double>(i) / kPacketsPerSecond;
        Simulator::Schedule(Seconds(tS), &Generate, static_cast<uint64_t>(i), apAddress);
    }
    for (uint32_t i = 0; i <= 800; ++i)
    {
        Simulator::Schedule(Seconds(static_cast<double>(i) / 4.0), &RecordMobility);
    }

    Simulator::Stop(Seconds(kObserveUntilS));
    Simulator::Run();

    const double associatedS = g.totalAssociatedS +
        (g.associationOpen ? kObserveUntilS - g.associationStartS : 0.0);
    NS_ABORT_MSG_IF(g.generated != kPacketCount, "Incorrect number of generated messages");
    if (g.policy == "immediate")
    {
        NS_ABORT_MSG_IF(g.generated != g.dropNoAssociation + g.socketRejected +
                                           g.socketAccepted,
                        "Immediate disposition accounting failure");
    }
    else
    {
        NS_ABORT_MSG_IF(g.generated != g.overflowDropNewest + g.enqueued,
                        "FIFO generated accounting failure");
        NS_ABORT_MSG_IF(g.enqueued != g.expiredBeforeSend + g.bufferSendAttempts +
                                         g.queue.size(),
                        "FIFO queue conservation failure");
        NS_ABORT_MSG_IF(g.bufferSendAttempts != g.socketRejected + g.socketAccepted,
                        "FIFO socket submission accounting failure");
        NS_ABORT_MSG_IF(g.bufferedBytes != g.queue.size() * kPayloadBytes,
                        "FIFO buffer bytes accounting failure");
    }
    NS_ABORT_MSG_IF(g.uniqueReceived > g.socketAccepted,
                    "Received more unique messages than accepted by socket");
    NS_ABORT_MSG_IF(g.receivedOnTime + g.receivedLate != g.uniqueReceived,
                    "Deadline accounting failure");
    NS_ABORT_MSG_IF(g.maximumBufferedBytes > g.bufferLimitBytes,
                    "Exceeded buffer capacity");

    std::ofstream summary(prefix + "_summary.csv");
    NS_ABORT_MSG_IF(!summary.is_open(), "Cannot write summary CSV");
    summary << "speed_mps,stop_s,ap_x_m,seed,run,generated,drop_no_association,"
               "socket_rejected,socket_accepted,received_unique,received_on_time,"
               "received_late,duplicate_rx,malformed_rx,not_observed_after_socket_accept,"
               "associated_duration_s,assoc_events,deassoc_events,policy,"
               "buffer_enqueued,buffer_overflow,buffer_expired,buffer_sent_attempts,"
               "buffer_remaining,buffer_peak_bytes,buffer_limit_bytes,pacing_ms,"
               "path_loss_exponent,tx_dbm,wifi_standard,frequency_hz,"
               "scenario,background_rate_bps,background_rx_packets,background_rx_bytes,"
               "ignored_assoc_callbacks,ignored_deassoc_callbacks\n";
    summary << std::fixed << std::setprecision(9)
            << speed << ',' << stopSeconds << ',' << apX << ',' << seed << ',' << run
            << ',' << g.generated << ',' << g.dropNoAssociation << ','
            << g.socketRejected << ',' << g.socketAccepted << ','
            << g.uniqueReceived << ',' << g.receivedOnTime << ','
            << g.receivedLate << ',' << g.duplicateReceived << ','
            << g.malformedReceived << ','
            << (g.socketAccepted - g.uniqueReceived) << ','
            << associatedS << ',' << g.associationEvents << ','
            << g.disassociationEvents << ',' << g.policy << ','
            << g.enqueued << ',' << g.overflowDropNewest << ','
            << g.expiredBeforeSend << ',' << g.bufferSendAttempts << ','
            << g.queue.size() << ',' << g.maximumBufferedBytes << ','
            << g.bufferLimitBytes << ',' << g.pacingMs << ','
            << exponent << ',' << txDbm << ",802.11g,2412000000,"
            << scenario << ',' << (scenario == "contention" ? backgroundRateBps : 0)
            << ',' << g.backgroundRxPackets << ',' << g.backgroundRxBytes
            << ',' << g.ignoredAssocCallbacks << ',' << g.ignoredDeassocCallbacks << '\n';

    std::cout << "P3 ns-3.48: scenario=" << g.scenario << ", policy=" << g.policy
              << ", speed=" << speed << " m/s, stop=" << stopSeconds
              << " s, seed=" << seed << ", run=" << run << '\n'
              << "Generated=" << g.generated << ", no-association drops="
              << g.dropNoAssociation << ", buffer overflow=" << g.overflowDropNewest
              << ", buffer expired=" << g.expiredBeforeSend << '\n'
              << "Socket accepted=" << g.socketAccepted
              << ", rejected=" << g.socketRejected
              << ", received unique=" << g.uniqueReceived
              << ", on time <=60s=" << g.receivedOnTime
              << ", late=" << g.receivedLate << '\n'
              << "Accepted but not observed=" << g.socketAccepted - g.uniqueReceived
              << ", assoc=" << g.associationEvents
              << ", deassoc=" << g.disassociationEvents
              << ", assoc seconds=" << associatedS << '\n'
              << "Competing STA RX at AP=" << g.backgroundRxPackets
              << " packets (" << g.backgroundRxBytes << " bytes)\n"
              << "Ignored Assoc/DeAssoc callbacks=" << g.ignoredAssocCallbacks
              << "/" << g.ignoredDeassocCallbacks << "\n"
              << "FIFO peak=" << g.maximumBufferedBytes << " bytes, remaining="
              << g.queue.size() << " messages, pacing=" << g.pacingMs << " ms\n"
              << "CSV prefix: " << prefix << '\n';

    Simulator::Destroy();
    return 0;
}
