// COMOV B10 - P1: continuous bus mobility, Wi-Fi association, immediate UDP.
// Target: ns-3.48. Pilot ONLY: no application buffer and no main-run statistics.
// All 1000-byte UDP payloads contain a 16-byte [sequence,generation_ns] header.

#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/propagation-module.h"
#include "ns3/wifi-module.h"

#include <array>
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

struct Pilot
{
    Ptr<ConstantVelocityMobilityModel> bus;
    Ptr<ConstantPositionMobilityModel> ap;
    Ptr<StaWifiMac> mac;
    Ptr<LogDistancePropagationLossModel> loss;
    Ptr<Socket> sender;
    double speed{5.0};
    double stopSeconds{10.0};
    double apX{0.0};
    double txDbm{20.0};
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
    bool associationOpen{false};
    double associationStartS{0.0};
    double totalAssociatedS{0.0};
    std::set<uint64_t> uniqueIds;
    std::ofstream generatedCsv;
    std::ofstream receivedCsv;
    std::ofstream associationCsv;
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

void
OnAssociation(Mac48Address apMac)
{
    const double now = Simulator::Now().GetSeconds();
    ++g.associationEvents;
    if (!g.associationOpen)
    {
        g.associationOpen = true;
        g.associationStartS = now;
    }
    g.associationCsv << now << ",assoc," << apMac << ','
                     << g.bus->GetPosition().x << ',' << Distance3d() << '\n';
}

void
OnDisassociation(Mac48Address apMac)
{
    const double now = Simulator::Now().GetSeconds();
    ++g.disassociationEvents;
    if (g.associationOpen)
    {
        g.totalAssociatedS += now - g.associationStartS;
        g.associationOpen = false;
    }
    g.associationCsv << now << ",deassoc," << apMac << ','
                     << g.bus->GetPosition().x << ',' << Distance3d() << '\n';
}

void
RecordMobility()
{
    const auto pos = g.bus->GetPosition();
    const auto velocity = g.bus->GetVelocity();
    const bool associated = g.mac->IsAssociated();
    const double predictedRxDbm = g.loss->CalcRxPower(g.txDbm, g.ap, g.bus);
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
Generate(uint64_t sequence, Ipv4Address apAddress)
{
    const double nowS = Simulator::Now().GetSeconds();
    const uint64_t genNs = static_cast<uint64_t>(Simulator::Now().GetNanoSeconds());
    const bool associated = g.mac->IsAssociated();
    const double x = g.bus->GetPosition().x;
    ++g.generated;

    // Strict immediate policy: messages generated without an associated Wi-Fi
    // link are discarded at application level rather than queued for a
    // subsequent association. Nothing is buffered in the application.
    if (!associated)
    {
        ++g.dropNoAssociation;
        g.generatedCsv << sequence << ',' << nowS << ',' << x << ','
                       << Distance3d() << ",0,0,,no_association\n";
        return;
    }

    std::array<uint8_t, kPayloadBytes> payload{};
    WriteUInt64(payload.data(), sequence);
    WriteUInt64(payload.data() + 8, genNs);

    const Ptr<Packet> packet = Create<Packet>(payload.data(), kPayloadBytes);
    const int n = g.sender->SendTo(packet,
                                  0,
                                  InetSocketAddress(apAddress, kUdpPort));
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
    // SendTo success means accepted by UDP/IP socket, NOT received by the AP
    // and not necessarily transmitted immediately at the 802.11 MAC.
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
    std::string prefix{"p1"};
    uint32_t seed{1};
    uint64_t run{1};
    double speed{5.0};
    double stopSeconds{10.0};
    double apX{0.0};
    double exponent{3.0};
    double txDbm{20.0};

    CommandLine cmd(__FILE__);
    cmd.AddValue("prefix", "Output prefix, existing parent directory required", prefix);
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

    g.speed = speed;
    g.stopSeconds = stopSeconds;
    g.apX = apX;
    g.txDbm = txDbm;
    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(run);

    OpenCsv(g.generatedCsv, prefix + "_generated.csv",
            "seq,t_gen_s,bus_x_m,distance_ap_m,associated_at_generation,"
            "attempted_socket_send,send_return,drop_reason");
    OpenCsv(g.receivedCsv, prefix + "_received.csv",
            "seq,t_gen_s,t_rx_s,delay_s,on_time,duplicate,associated_at_reception");
    OpenCsv(g.associationCsv, prefix + "_association.csv",
            "t_s,event,ap_mac,bus_x_m,distance_ap_m");
    OpenCsv(g.mobilityCsv, prefix + "_mobility.csv",
            "t_s,bus_x_m,bus_velocity_mps,distance_ap_m,associated,pr_model_dbm");

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
    Ipv4AddressHelper addresses;
    addresses.SetBase("10.8.0.0", "255.255.255.0");
    NetDeviceContainer wifiDevices;
    wifiDevices.Add(apDevices);
    wifiDevices.Add(busDevices);
    const Ipv4InterfaceContainer interfaces = addresses.Assign(wifiDevices);
    const Ipv4Address apAddress = interfaces.GetAddress(0);

    Ptr<Socket> receiver = Socket::CreateSocket(apNode.Get(0),
                                                UdpSocketFactory::GetTypeId());
    NS_ABORT_MSG_IF(receiver->Bind(InetSocketAddress(Ipv4Address::GetAny(),
                                                   kUdpPort)) != 0,
                    "AP UDP receiver bind failed");
    receiver->SetRecvCallback(MakeCallback(&OnDatagram));

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
    NS_ABORT_MSG_IF(g.generated != g.dropNoAssociation + g.socketRejected +
                                       g.socketAccepted,
                    "Failed send disposition accounting");
    NS_ABORT_MSG_IF(g.uniqueReceived > g.socketAccepted,
                    "Received more unique packets than accepted by socket");
    NS_ABORT_MSG_IF(g.receivedOnTime + g.receivedLate != g.uniqueReceived,
                    "Received message deadline accounting mismatch");

    std::ofstream summary(prefix + "_summary.csv");
    NS_ABORT_MSG_IF(!summary.is_open(), "Cannot write summary CSV");
    summary << "speed_mps,stop_s,ap_x_m,seed,run,generated,drop_no_association,"
               "socket_rejected,socket_accepted,received_unique,received_on_time,"
               "received_late,duplicate_rx,malformed_rx,not_observed_after_socket_accept,"
               "associated_duration_s,assoc_events,deassoc_events,policy\n";
    summary << std::fixed << std::setprecision(9)
            << speed << ',' << stopSeconds << ',' << apX << ',' << seed << ',' << run
            << ',' << g.generated << ',' << g.dropNoAssociation << ','
            << g.socketRejected << ',' << g.socketAccepted << ','
            << g.uniqueReceived << ',' << g.receivedOnTime << ','
            << g.receivedLate << ',' << g.duplicateReceived << ','
            << g.malformedReceived << ','
            << (g.socketAccepted - g.uniqueReceived) << ','
            << associatedS << ',' << g.associationEvents << ','
            << g.disassociationEvents << ",immediate_drop_if_unassociated\n";

    std::cout << "P1 ns-3.48 802.11g: v=" << speed << " m/s, stop=" << stopSeconds
              << " s, run=" << run << '\n'
              << "Generated=" << g.generated
              << ", no-association drops=" << g.dropNoAssociation
              << ", socket accepted=" << g.socketAccepted
              << ", socket rejected=" << g.socketRejected << '\n'
              << "Unique received=" << g.uniqueReceived
              << ", on time (<=60s)=" << g.receivedOnTime
              << ", late=" << g.receivedLate
              << ", not observed after accepted send="
              << g.socketAccepted - g.uniqueReceived << '\n'
              << "Association events=" << g.associationEvents
              << ", deassociation events=" << g.disassociationEvents
              << ", observed associated seconds=" << associatedS << '\n'
              << "CSV prefix: " << prefix << '\n';

    Simulator::Destroy();
    return 0;
}
