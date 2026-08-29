"""
generate_cases.py
Builds cases.csv -- the 30-case NetSage AI dataset required by the
"AI + Network Troubleshooting" problem statement.

Each case bundles exactly what a junior engineer would have on hand:
  - symptom            : what the user/student reported
  - topology_note      : one line about the relevant part of the lab topology
  - show_output        : raw-ish CLI evidence (show ip int brief / show vlan / etc.)
  - expected_fault      : ground truth used to score the AI later
  - osi_layer          : ground truth OSI layer
  - concept_tag        : VLAN / GATEWAY / DHCP / DNS / ROUTING / ACL / NAT / WIRELESS
  - severity           : Sev1 (network/segment down), Sev2 (user impaired but working),
                          Sev3 (cosmetic / minor)
"""
import csv

CASES = [
# ---------------- VLAN (6) ----------------
dict(case_id="C001", concept_tag="VLAN", severity="Sev2", osi_layer="L2",
 symptom="PC in Room 101 gets an IP but cannot reach anything, including its own default gateway.",
 topology_note="PC101 patched into Sw2 Fa0/5, should be on VLAN 30 (Students).",
 show_output="Sw2#show interfaces fa0/5 switchport\nSwitchport: Enabled\nAdministrative Mode: static access\nOperational Mode: static access\nAccess Mode VLAN: 10 (Guest)\nVoice VLAN: none",
 expected_fault="Access port Fa0/5 is assigned to VLAN 10 (Guest) instead of VLAN 30 (Students)."),

dict(case_id="C002", concept_tag="VLAN", severity="Sev1", osi_layer="L2",
 symptom="All PCs on the new Accounting branch lost connectivity to each other after a switch reload.",
 topology_note="Sw3 trunk to Core carries VLANs 10,20,30,40.",
 show_output="Sw3#show interfaces trunk\nPort   Mode   Encapsulation  Status   Native vlan\nGi0/1  on     802.1q         trunking 1\nPort   Vlans allowed on trunk\nGi0/1  10,20,30",
 expected_fault="VLAN 40 (Accounting) is missing from the allowed VLAN list on the Gi0/1 trunk, so it is being pruned."),

dict(case_id="C003", concept_tag="VLAN", severity="Sev3", osi_layer="L2",
 symptom="One printer in the lab is unreachable from its own VLAN but everything else on that VLAN works.",
 topology_note="Printer connects to Sw1 Fa0/12.",
 show_output="Sw1#show vlan brief\nVLAN Name       Status  Ports\n20   Faculty    active  Fa0/1-11, Fa0/13-24\n(VLAN 20 does not list Fa0/12)\nSw1#show interfaces fa0/12 switchport\nAccess Mode VLAN: 999 (inactive)",
 expected_fault="Fa0/12 is assigned to VLAN 999, which does not exist / is not active on this switch."),

dict(case_id="C004", concept_tag="VLAN", severity="Sev2", osi_layer="L2",
 symptom="New laptop cannot get past 'obtaining IP address' when plugged into the library switch.",
 topology_note="Library port should be access VLAN 50; DHCP relay is configured on the router subinterface for VLAN 50.",
 show_output="SwLib#show interfaces fa0/8 switchport\nAdministrative Mode: trunk\nOperational Mode: trunk\n",
 expected_fault="Port Fa0/8 was left configured as a trunk port instead of a VLAN 50 access port, so the PC never gets an access-VLAN and DHCP fails."),

dict(case_id="C005", concept_tag="VLAN", severity="Sev2", osi_layer="L2",
 symptom="Voice VLAN phone registers but the PC daisy-chained behind it cannot reach the gateway.",
 topology_note="Fa0/6 configured with a voice VLAN and a data VLAN.",
 show_output="Sw4#show interfaces fa0/6 switchport\nAccess Mode VLAN: 30 (Students)\nVoice VLAN: 100 (Voice)\n(PC subnet is actually VLAN 31, not 30)",
 expected_fault="Data access VLAN on Fa0/6 is set to 30 but the PC's cabling/subnet belongs to VLAN 31."),

dict(case_id="C006", concept_tag="VLAN", severity="Sev1", osi_layer="L2",
 symptom="Two switches show conflicting VLAN databases after a technician added a VLAN locally.",
 topology_note="Sw5 and Sw6 are both VTP clients of the same domain.",
 show_output="Sw5#show vtp status\nVTP Version: 2\nConfiguration Revision: 12\nSw6#show vtp status\nConfiguration Revision: 4",
 expected_fault="Sw5 has a higher VTP revision number than the domain server, so it may have overwritten the VLAN database domain-wide."),

# ---------------- GATEWAY (5) ----------------
dict(case_id="C007", concept_tag="GATEWAY", severity="Sev1", osi_layer="L3",
 symptom="Entire VLAN 30 subnet can talk to each other but nothing can leave the subnet.",
 topology_note="PCs configured with gateway 192.168.30.1.",
 show_output="PC>ipconfig\nIPv4 Address: 192.168.30.55\nSubnet Mask: 255.255.255.0\nDefault Gateway: 192.168.30.1\nRouter#show ip interface brief\nGigabitEthernet0/0.30  192.168.30.254  YES manual up up",
 expected_fault="PCs are pointed at 192.168.30.1 but the actual router subinterface for VLAN 30 is 192.168.30.254 -- default gateway mismatch."),

dict(case_id="C008", concept_tag="GATEWAY", severity="Sev2", osi_layer="L3",
 symptom="One PC can ping the gateway but no other PC on the same VLAN can.",
 topology_note="Static IP configured manually on the affected PC.",
 show_output="PC>ipconfig\nIPv4 Address: 192.168.20.10\nSubnet Mask: 255.255.255.0\nDefault Gateway: 192.168.10.1",
 expected_fault="Default gateway (192.168.10.1) is on a different subnet than the PC's own IP (192.168.20.0/24)."),

dict(case_id="C009", concept_tag="GATEWAY", severity="Sev1", osi_layer="L3",
 symptom="Whole branch lost access to everything outside the local subnet at the same time.",
 topology_note="HSRP pair R1/R2 provide the gateway VIP for VLAN 10.",
 show_output="R1#show standby brief\nInterface  Grp  State  Active   Standby   Virtual IP\nGi0/1      10   Standby  unknown  local     192.168.10.1\nR2#show standby brief -- no output (process not running)",
 expected_fault="HSRP active router R2 is down/unreachable, and R1 has not taken over the virtual gateway IP."),

dict(case_id="C010", concept_tag="GATEWAY", severity="Sev2", osi_layer="L3",
 symptom="New DHCP clients get an address but cannot reach the gateway; static PCs on same VLAN are fine.",
 topology_note="DHCP pool default-router entry recently edited.",
 show_output="Router#show run | section pool VLAN30\nip dhcp pool VLAN30\n network 192.168.30.0 255.255.255.0\n default-router 192.168.30.1",
 expected_fault="DHCP pool is handing out default-router 192.168.30.1 but the interface is actually 192.168.30.254 -- scope option mismatch."),

dict(case_id="C011", concept_tag="GATEWAY", severity="Sev3", osi_layer="L3",
 symptom="Intermittent 'destination host unreachable' only from one PC, others on same VLAN fine.",
 topology_note="Duplicate static IP suspected.",
 show_output="Router#show arp\nInternet  192.168.40.20  0  0011.2233.4455  ARPA  Gi0/2\nInternet  192.168.40.20  0  00aa.bbcc.ddee  ARPA  Gi0/2",
 expected_fault="Two different MAC addresses are resolving to the same IP 192.168.40.20 -- duplicate IP assignment causing intermittent ARP flapping."),

# ---------------- DHCP (4) ----------------
dict(case_id="C012", concept_tag="DHCP", severity="Sev2", osi_layer="L3",
 symptom="Several new PCs on VLAN 40 stuck on APIPA (169.254.x.x) address.",
 topology_note="DHCP server is centralized on the router; relay configured on switch uplink.",
 show_output="Router#show ip dhcp pool\nPool VLAN40 : \n Utilization mark (high/low) : 100 / 0\n Subnet size (first/next) : 0 / 0\n Total addresses : 0",
 expected_fault="DHCP pool VLAN40 has zero addresses defined (empty/misconfigured network statement), so clients time out and self-assign APIPA."),

dict(case_id="C013", concept_tag="DHCP", severity="Sev1", osi_layer="L3",
 symptom="Whole new classroom of 20 PCs cannot get an IP address at all.",
 topology_note="Classroom is on VLAN 60, router-on-a-stick subinterface newly added.",
 show_output="Router#show ip dhcp binding -- empty\nRouter#show run int gi0/0.60\ninterface GigabitEthernet0/0.60\n encapsulation dot1Q 60\n(no ip helper-address configured on switch SVI upstream)",
 expected_fault="No ip helper-address is forwarding DHCP broadcasts from VLAN 60 to the DHCP server, so requests never arrive."),

dict(case_id="C014", concept_tag="DHCP", severity="Sev3", osi_layer="L3",
 symptom="A returning laptop keeps getting a different IP each day, breaking a printer share that was IP-pinned.",
 topology_note="Lease time was shortened during a lab exercise.",
 show_output="Router#show run | section pool VLAN20\nip dhcp pool VLAN20\n lease 0 0 5",
 expected_fault="DHCP lease time was set to 5 minutes, so addresses are churning far more than expected."),

dict(case_id="C015", concept_tag="DHCP", severity="Sev2", osi_layer="L3",
 symptom="Two PCs on the same VLAN keep getting the exact same IP address and knocking each other offline.",
 topology_note="A static reservation overlaps the dynamic pool range.",
 show_output="Router#show run | section pool VLAN30\nip dhcp pool VLAN30\n network 192.168.30.0 255.255.255.0\nip dhcp excluded-address 192.168.30.1 192.168.30.9\n(static PC configured with 192.168.30.50, which is inside the dynamic range)",
 expected_fault="A statically-assigned address (192.168.30.50) falls inside the active DHCP scope and was not excluded, causing an IP collision."),

# ---------------- DNS (4) ----------------
dict(case_id="C016", concept_tag="DNS", severity="Sev2", osi_layer="L7",
 symptom="Students can ping the file server by IP but 'server not found' when browsing to it by name.",
 topology_note="Internal DNS server is 192.168.10.5.",
 show_output="PC>ipconfig /all\nDNS Servers: 192.168.10.6\n(actual internal DNS server is 192.168.10.5)",
 expected_fault="PCs are pointed at the wrong DNS server address (192.168.10.6 instead of .5), so name resolution fails while IP connectivity is fine."),

dict(case_id="C017", concept_tag="DNS", severity="Sev3", osi_layer="L7",
 symptom="One internal hostname resolves to an old, decommissioned IP address.",
 topology_note="Server was re-IP'd last week during the VLAN 40 migration.",
 show_output="DNS Server#show host filesrv.college.local\nfilesrv.college.local  A  192.168.40.15  (old address; server now on 192.168.40.115)",
 expected_fault="Stale A record for filesrv.college.local still points to the pre-migration IP -- DNS record was never updated."),

dict(case_id="C018", concept_tag="DNS", severity="Sev2", osi_layer="L7",
 symptom="External websites fail to resolve for the whole building but internal name lookups work fine.",
 topology_note="Internal DNS is configured to forward unknown queries to an upstream/public resolver.",
 show_output="DNS Server#show run | include forwarder\n(no forwarder configured)",
 expected_fault="Internal DNS server has no upstream forwarder configured, so it cannot resolve any name outside its own zone."),

dict(case_id="C019", concept_tag="DNS", severity="Sev3", osi_layer="L7",
 symptom="Browsing to the intranet portal is slow the first time each morning, then fine.",
 topology_note="DNS record TTL was set very low during testing and never reverted.",
 show_output="DNS Server#show host portal.college.local\nportal.college.local  A  192.168.10.20  TTL=10",
 expected_fault="TTL on the portal record is set to 10 seconds, forcing constant re-resolution instead of caching."),

# ---------------- ROUTING (4) ----------------
dict(case_id="C020", concept_tag="ROUTING", severity="Sev1", osi_layer="L3",
 symptom="Branch A cannot reach Branch B at all; both branches can reach the Internet fine.",
 topology_note="R1 (Branch A) and R2 (Branch B) run OSPF over a WAN link, area 0.",
 show_output="R1#show ip route ospf -- (no OSPF routes present)\nR1#show ip ospf neighbor -- empty",
 expected_fault="OSPF neighbor relationship between R1 and R2 never formed (no neighbors listed), so inter-branch routes are missing."),

dict(case_id="C021", concept_tag="ROUTING", severity="Sev2", osi_layer="L3",
 symptom="Traffic from VLAN 30 to the server farm VLAN takes a slow, extra hop through the old core switch.",
 topology_note="Two equal paths exist; one route was manually configured with a lower preference.",
 show_output="R1#show ip route 192.168.50.0\nRouting entry for 192.168.50.0/24\n Known via 'static', distance 1, metric 0\n(a better OSPF route with distance 110 exists but is not preferred because static distance is lower)",
 expected_fault="A manually-added static route with a lower administrative distance is overriding the better OSPF path to the server farm."),

dict(case_id="C022", concept_tag="ROUTING", severity="Sev1", osi_layer="L3",
 symptom="After a router reboot, the whole new branch lost its route to the Internet.",
 topology_note="Default route was configured but not saved before the reboot.",
 show_output="R3#show ip route\nGateway of last resort is not set\nR3#show run | include ip route\n(no output)",
 expected_fault="The default route (ip route 0.0.0.0 0.0.0.0 <next-hop>) was never saved to the startup-config and was lost on reload."),

dict(case_id="C023", concept_tag="ROUTING", severity="Sev2", osi_layer="L3",
 symptom="Users can reach the server subnet but replies never come back, one-way connectivity.",
 topology_note="New subnet 192.168.70.0/24 was added behind R4.",
 show_output="Core#show ip route 192.168.70.0 -- % Network not in table",
 expected_fault="The core router has no route back to the new 192.168.70.0/24 subnet -- missing/unadvertised return route."),

# ---------------- ACL (4) ----------------
dict(case_id="C024", concept_tag="ACL", severity="Sev2", osi_layer="L3/L4",
 symptom="Students in VLAN 30 can ping the file server but cannot open the shared folder (SMB).",
 topology_note="An ACL was added on R1 Gi0/0.30 to restrict server-farm access.",
 show_output="R1#show access-lists 101\nExtended IP access list 101\n 10 permit icmp 192.168.30.0 0.0.0.255 any\n 20 deny ip 192.168.30.0 0.0.0.255 192.168.50.0 0.0.0.255\n 30 permit ip any any",
 expected_fault="ACL 101 explicitly denies IP traffic (which blocks TCP/SMB) from VLAN 30 to the server farm while only permitting ICMP -- overly restrictive rule ordering."),

dict(case_id="C025", concept_tag="ACL", severity="Sev1", osi_layer="L3/L4",
 symptom="After applying a new security ACL, the whole VLAN 30 subnet lost all outbound access, including web.",
 topology_note="ACL applied inbound on the VLAN 30 subinterface.",
 show_output="R1#show access-lists 110\nExtended IP access list 110\n 10 permit tcp any any eq 443\n(implicit deny any any at the end)",
 expected_fault="ACL 110 only explicitly permits HTTPS; every other protocol (DNS, HTTP, ICMP) is silently dropped by the implicit deny at the end of the list."),

dict(case_id="C026", concept_tag="ACL", severity="Sev3", osi_layer="L3/L4",
 symptom="One specific server can be pinged by everyone except the admin's own PC.",
 topology_note="A host-specific deny rule was added above the general permit rule.",
 show_output="R1#show access-lists 120\nExtended IP access list 120\n 10 deny icmp host 192.168.30.99 host 192.168.50.10\n 20 permit ip any any",
 expected_fault="Line 10 specifically denies ICMP from the admin's host (192.168.30.99) to the server, and it is evaluated before the general permit."),

dict(case_id="C027", concept_tag="ACL", severity="Sev2", osi_layer="L3/L4",
 symptom="Guest Wi-Fi users can reach the internal file server, which should be blocked.",
 topology_note="ACL meant to isolate the Guest VLAN from internal subnets.",
 show_output="R1#show access-lists 130\nExtended IP access list 130\n 10 permit ip any any\n(no deny rules present)",
 expected_fault="The guest-isolation ACL 130 only contains a permit-any rule; the intended deny statements to internal subnets were never added."),

# ---------------- NAT (3) ----------------
dict(case_id="C028", concept_tag="NAT", severity="Sev1", osi_layer="L3",
 symptom="No PC in the building can reach the Internet, but internal traffic between VLANs is fine.",
 topology_note="NAT overload configured on the edge router's outside interface.",
 show_output="Edge#show ip nat statistics\nTotal active translations: 0\nOutside interfaces: (none)\nInside interfaces: Gi0/1",
 expected_fault="No interface is marked as the NAT outside interface, so 'ip nat inside source' never triggers -- NAT is not actually translating."),

dict(case_id="C029", concept_tag="NAT", severity="Sev2", osi_layer="L3",
 symptom="Internet works for most PCs but a specific server that needs inbound access from outside is unreachable externally.",
 topology_note="Static NAT was supposed to map the server's private IP to a public IP.",
 show_output="Edge#show ip nat translations\n(no static entries; only dynamic overload entries present)",
 expected_fault="The required static NAT entry (ip nat inside source static 192.168.50.10 <public-ip>) for the server was never configured."),

dict(case_id="C030", concept_tag="NAT", severity="Sev3", osi_layer="L3",
 symptom="Two branches using the same private subnet range cannot reach each other over the new site-to-site link.",
 topology_note="Both branches use 192.168.1.0/24 internally.",
 show_output="R1#show run | include ip nat\nip nat inside source list 1 interface Gi0/0 overload\n(same overlapping subnet configured at both ends, no NAT applied on the tunnel path)",
 expected_fault="Overlapping private subnets (192.168.1.0/24 at both branches) are not being translated across the site-to-site link, causing routing ambiguity."),

# ---------------- WIRELESS (2, incl. the worked example from the brief) ----------------
dict(case_id="C031", concept_tag="WIRELESS", severity="Sev1", osi_layer="L2/L3",
 symptom="Guest Wi-Fi can reach internal server resources, which should never happen.",
 topology_note="Guest SSID is mapped to VLAN 15; internal server farm is VLAN 50.",
 show_output="WLC#show wlan 2\nSSID: Guest-WiFi  Interface/Interface Group(G): vlan15\nSw-AP#show interfaces trunk\nGi0/1  Vlans allowed: 1,10,15,50",
 expected_fault="Guest VLAN 15 is trunked alongside the internal server VLAN 50 with no isolating ACL -- guest traffic is not segmented from internal resources."),

dict(case_id="C032", concept_tag="WIRELESS", severity="Sev2", osi_layer="L1/L2",
 symptom="Students near the far end of the library keep getting dropped from Wi-Fi, wired PCs unaffected.",
 topology_note="Single AP covers the whole library floor.",
 show_output="AP1#show controllers dot11Radio 0 | include Power\nTransmit Power: 5 dBm (low)\nAP1#show interface dot11radio0 -- CRC errors: high",
 expected_fault="AP transmit power is set very low (5 dBm) for the coverage area, causing weak signal and drops at distance -- RF/coverage issue, not switching."),
]

fieldnames = ["case_id","concept_tag","severity","osi_layer","symptom","topology_note","show_output","expected_fault"]

with open("cases.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for c in CASES:
        w.writerow(c)

print(f"Wrote {len(CASES)} cases to cases.csv")
