// COMOV B10 - P0: static-distance propagation and decoded Wi-Fi frame RSS.
// Target: ns-3.48. No UDP, bus movement or buffering in this pilot.
// Compilation/execution must be verified in the group's WSL ns-3.48 installation.

#include "ns3/core-module.h"
#include "ns3/mobility-module.h"
#include "ns3/propagation-module.h"
#include "ns3/wifi-module.h"

#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

using namespace ns3;

namespace
{
constexpr double kLightSpeed = 299792458.0;
constexpr double kPi = 3.14159265358979323846;

struct Sample
{
    double horizontalM{0};
    double distance3dM{0};
    double theoreticalPrDbm{0};
    double modelPrDbm{0};
    uint64_t decodedFrames{0};
    double signalSumDbm{0};
};

std::vector<Sample> g_samples;
std::size_t g_currentSample{0};
double g_sampleStartS{0};
double g_settlingS{0.25};

double
FreeSpacePathLossDb(double frequencyHz, double distanceM)
{
    return 20.0 * std::log10(4.0 * kPi * frequencyHz * distanceM / kLightSpeed);
}

// Fires for frames decoded at the STA PHY. The received RSS is not available
// in this callback when no frame can be decoded; such cases remain empty in CSV.
void
DecodedAtSta(Ptr<const Packet> /* packet */,
             uint16_t /* channelFreqMhz */,
             WifiTxVector /* txVector */,
             MpduInfo /* aMpdu */,
             SignalNoiseDbm signalNoise,
             uint16_t /* staId */)
{
    if (Simulator::Now().GetSeconds() - g_sampleStartS < g_settlingS)
    {
        return;
    }
    auto& s = g_samples.at(g_currentSample);
    ++s.decodedFrames;
    s.signalSumDbm += signalNoise.signal;
}

void
PlaceSta(Ptr<ConstantPositionMobilityModel> sta,
         Ptr<ConstantPositionMobilityModel> ap,
         Ptr<LogDistancePropagationLossModel> loss,
         std::size_t index,
         double horizontalM,
         double apHeightM,
         double staHeightM,
         double txPowerDbm,
         double frequencyHz,
         double exponent,
         double referenceDistanceM,
         double referenceLossDb)
{
    sta->SetPosition(Vector(horizontalM, 0.0, staHeightM));
    g_currentSample = index;
    g_sampleStartS = Simulator::Now().GetSeconds();

    Sample& s = g_samples.at(index);
    s.horizontalM = horizontalM;
    const Vector apPos = ap->GetPosition();
    const Vector staPos = sta->GetPosition();
    s.distance3dM = std::sqrt(std::pow(apPos.x - staPos.x, 2) +
                             std::pow(apPos.y - staPos.y, 2) +
                             std::pow(apPos.z - staPos.z, 2));

    const double lossTheory = referenceLossDb +
        10.0 * exponent * std::log10(s.distance3dM / referenceDistanceM);
    s.theoreticalPrDbm = txPowerDbm - lossTheory;
    s.modelPrDbm = loss->CalcRxPower(txPowerDbm, ap, sta);
}

void
WriteCsv(const std::string& filename,
         const std::string& standard,
         double frequencyHz,
         double exponent,
         double referenceLossDb)
{
    std::ofstream file(filename);
    NS_ABORT_MSG_IF(!file.is_open(), "Could not open CSV file: " << filename);
    file << std::fixed << std::setprecision(6);
    file << "standard,frequency_hz,path_loss_exponent,reference_loss_db,"
            "horizontal_m,distance_3d_m,theoretical_pr_dbm,ns3_model_pr_dbm,"
            "model_minus_theory_db,decoded_frames_at_sta,phy_rss_mean_dbm,"
            "phy_minus_model_db\n";

    for (const auto& s : g_samples)
    {
        file << standard << ',' << frequencyHz << ',' << exponent << ','
             << referenceLossDb << ',' << s.horizontalM << ','
             << s.distance3dM << ',' << s.theoreticalPrDbm << ','
             << s.modelPrDbm << ','
             << (s.modelPrDbm - s.theoreticalPrDbm) << ','
             << s.decodedFrames << ',';
        if (s.decodedFrames != 0)
        {
            const double avg = s.signalSumDbm / s.decodedFrames;
            file << avg << ',' << (avg - s.modelPrDbm);
        }
        else
        {
            // Preserve both empty CSV columns (RSS and PHY-minus-model).
            file << ',';
        }
        // Empty RSS fields mean that the STA did not decode Wi-Fi frames
        // during the stationary part of this interval.
        file << '\n';
    }
}
} // namespace

int
main(int argc, char* argv[])
{
    std::string standard{"11g"};
    std::string csv{"p0_measurements.csv"};
    double txPowerDbm{20.0};
    double exponent{3.0};
    double apHeightM{4.0};
    double staHeightM{2.5};
    double slotSeconds{2.0};
    double settlingS{0.25};

    CommandLine cmd(__FILE__);
    cmd.AddValue("standard", "11g (2.412 GHz) or 11a (5.180 GHz)", standard);
    cmd.AddValue("csv", "CSV output path; parent directory must exist", csv);
    cmd.AddValue("txPowerDbm", "Tx power [dBm]", txPowerDbm);
    cmd.AddValue("exponent", "Log-distance path-loss exponent", exponent);
    cmd.AddValue("apHeightM", "AP antenna height [m]", apHeightM);
    cmd.AddValue("staHeightM", "STA antenna height [m]", staHeightM);
    cmd.AddValue("slotSeconds", "Time at each static-distance step [s]", slotSeconds);
    cmd.AddValue("settlingS", "Guard time after each step [s]", settlingS);
    cmd.Parse(argc, argv);

    NS_ABORT_MSG_IF(standard != "11g" && standard != "11a",
                    "--standard must be 11g or 11a");
    NS_ABORT_MSG_IF(exponent <= 0 || slotSeconds <= settlingS ||
                    settlingS < 0 || apHeightM == staHeightM,
                    "Invalid exponent, slot, settling time or antenna heights");

    const double frequencyHz = (standard == "11g") ? 2.412e9 : 5.180e9;
    const double referenceDistanceM = 1.0;
    const double referenceLossDb = FreeSpacePathLossDb(frequencyHz, referenceDistanceM);

    // IMPORTANT: by default, ns-3 LogDistance ReferenceLoss is referenced
    // to ~5.15 GHz. Explicitly set FSPL at the configured frequency.
    auto loss = CreateObject<LogDistancePropagationLossModel>();
    loss->SetAttribute("Exponent", DoubleValue(exponent));
    loss->SetAttribute("ReferenceDistance", DoubleValue(referenceDistanceM));
    loss->SetAttribute("ReferenceLoss", DoubleValue(referenceLossDb));

    auto channel = CreateObject<YansWifiChannel>();
    channel->SetPropagationDelayModel(CreateObject<ConstantSpeedPropagationDelayModel>());
    channel->SetPropagationLossModel(loss);

    WifiHelper wifi;
    wifi.SetStandard((standard == "11g") ? WIFI_STANDARD_80211g : WIFI_STANDARD_80211a);
    // PHY modes are band-dependent in ns-3.48: 802.11g / 2.4 GHz must
    // use ERP-OFDM, whereas 802.11a / 5 GHz uses OFDM.
    // The initial P0 checked management frames only, so it did not reveal
    // the invalid data-rate mode that caused the first P1 UDP run to abort.
    const std::string phyMode =
        (standard == "11g") ? "ErpOfdmRate6Mbps" : "OfdmRate6Mbps";
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                 "DataMode", StringValue(phyMode),
                                 "ControlMode", StringValue(phyMode));

    YansWifiPhyHelper phy;
    phy.SetChannel(channel);
    phy.Set("TxPowerStart", DoubleValue(txPowerDbm));
    phy.Set("TxPowerEnd", DoubleValue(txPowerDbm));
    phy.Set("TxPowerLevels", UintegerValue(1));
    phy.Set("TxGain", DoubleValue(0.0));
    phy.Set("RxGain", DoubleValue(0.0));
    phy.Set("ChannelSettings",
            StringValue((standard == "11g") ? "{1, 20, BAND_2_4GHZ, 0}"
                                            : "{36, 20, BAND_5GHZ, 0}"));

    NodeContainer apNode;
    NodeContainer staNode;
    apNode.Create(1);
    staNode.Create(1);

    MobilityHelper mobility;
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(apNode);
    mobility.Install(staNode);
    auto ap = apNode.Get(0)->GetObject<ConstantPositionMobilityModel>();
    auto sta = staNode.Get(0)->GetObject<ConstantPositionMobilityModel>();
    ap->SetPosition(Vector(0.0, 0.0, apHeightM));
    sta->SetPosition(Vector(0.0, 0.0, staHeightM));

    Ssid ssid{"COMOV-B10-P0"};
    WifiMacHelper mac;
    mac.SetType("ns3::ApWifiMac", "Ssid", SsidValue(ssid));
    wifi.Install(phy, mac, apNode);
    mac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(ssid),
                "ActiveProbing", BooleanValue(true));
    NetDeviceContainer staDevices = wifi.Install(phy, mac, staNode);

    auto staWifi = DynamicCast<WifiNetDevice>(staDevices.Get(0));
    NS_ABORT_MSG_IF(staWifi == nullptr, "STA device is not a WifiNetDevice");
    const bool connected = staWifi->GetPhy()->TraceConnectWithoutContext(
        "MonitorSnifferRx", MakeCallback(&DecodedAtSta));
    NS_ABORT_MSG_IF(!connected, "MonitorSnifferRx trace not connected");

    const std::vector<double> horizontalDistances{0, 5, 10, 20, 50, 100, 200};
    g_samples.resize(horizontalDistances.size());
    g_settlingS = settlingS;

    // AP and STA remain fixed within each slot. At every boundary the STA
    // jumps to a new location: this is NOT a continuous moving-bus model.
    PlaceSta(sta, ap, loss, 0, horizontalDistances[0], apHeightM, staHeightM,
             txPowerDbm, frequencyHz, exponent, referenceDistanceM, referenceLossDb);
    for (std::size_t i = 1; i < horizontalDistances.size(); ++i)
    {
        Simulator::Schedule(Seconds(slotSeconds * i),
                            &PlaceSta, sta, ap, loss, i, horizontalDistances[i],
                            apHeightM, staHeightM, txPowerDbm, frequencyHz,
                            exponent, referenceDistanceM, referenceLossDb);
    }

    Simulator::Stop(Seconds(slotSeconds * horizontalDistances.size()));
    Simulator::Run();
    WriteCsv(csv, standard, frequencyHz, exponent, referenceLossDb);

    std::cout << std::fixed << std::setprecision(4)
              << "P0: ns-3.48, IEEE 802." << standard << ", f="
              << frequencyHz / 1e9 << " GHz, ReferenceLoss(1 m)="
              << referenceLossDb << " dB\n"
              << "Saved " << g_samples.size() << " positions to " << csv << "\n";
    for (const auto& s : g_samples)
    {
        std::cout << "h=" << s.horizontalM << " m, d3d=" << s.distance3dM
                  << " m, model=" << s.modelPrDbm << " dBm, decoded="
                  << s.decodedFrames << "\n";
    }

    Simulator::Destroy();
    return 0;
}
