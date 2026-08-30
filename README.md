# NetSage AI

## AI-Assisted Troubleshooting Helper for Cisco Packet Tracer Labs

NetSage AI is an AI-assisted network troubleshooting system designed to help students and junior learners diagnose common networking problems in Cisco Packet Tracer and similar laboratory environments.

The system combines deterministic Python-based rule checking with an AI diagnosis layer. It analyses a reported network symptom together with topology information and relevant show-command output, identifies a probable root cause, and provides supporting evidence, a recommended next diagnostic command, and suggested corrective steps.

The project follows a human-in-the-loop approach. AI-generated diagnoses are treated as recommendations and are reviewed by a human before being accepted as a final troubleshooting result.

## Project Objectives

The main objectives of NetSage AI are:

- Develop an AI-assisted troubleshooting helper for Cisco Packet Tracer laboratory scenarios.
- Create a labelled dataset of network troubleshooting cases.
- Cover common networking fault categories.
- Provide the AI model with troubleshooting evidence rather than relying only on textual symptoms.
- Implement deterministic Python checks for common configuration errors.
- Require human review of every AI-generated diagnosis.
- Maintain records of accepted, edited, and rejected diagnoses.
- Provide a dashboard for analysing troubleshooting activity and AI-human agreement.
- Demonstrate a responsible approach to using AI in network troubleshooting.

## Problem Statement

Students and junior network engineers may know individual networking commands but still face difficulty connecting a network symptom with its actual root cause.

For example, a computer may receive an IP address and successfully communicate with its default gateway while still being unable to access a server. The underlying problem may involve VLAN configuration, inter-VLAN routing, DHCP, DNS, ACLs, NAT, or another network configuration issue.

NetSage AI addresses this problem by providing a structured troubleshooting workflow that combines network evidence, deterministic checks, AI-assisted reasoning, and human review.

## Key Features

### 1. Network Symptom Analysis

The system accepts information such as:

- Observed network symptom
- Topology information
- Relevant show-command output
- Networking category
- Severity

### 2. Deterministic Rule Checker

The Python-based rule checker identifies common configuration problems, including:

- Duplicate IP addresses
- Incorrect subnet masks
- Gateway mismatches
- Administratively down interfaces
- VLAN configuration inconsistencies
- Missing VLANs
- Missing routing entries
- Other basic configuration issues supported by the implemented rules

### 3. AI-Assisted Diagnosis

The AI component generates a structured troubleshooting response containing:

- OSI layer
- Confidence level
- Issue category
- Probable root cause
- Supporting evidence
- Recommended next command
- Suggested fix steps

When the available evidence is insufficient, the system is designed to recommend an appropriate next diagnostic command instead of presenting an unsupported conclusion as certain.

### 4. Human Review

Every AI-generated diagnosis is reviewed by a human.

The reviewer can:

- Accept the diagnosis
- Edit the diagnosis
- Reject the diagnosis

The review result is stored for later evaluation.

### 5. Responsible AI Log

Edited and rejected diagnoses are recorded to identify situations where the AI recommendation does not fully match the available network evidence.

This provides a record for evaluating the limitations and reliability of the AI component.

### 6. Troubleshooting Dataset

The project contains 32 labelled representative troubleshooting cases covering:

- VLAN
- IP Addressing
- DHCP
- DNS
- Routing
- NAT/ACL
- Wireless
- Physical Layer
- Layer-2 Infrastructure
- Spanning Tree
- Port Security
- EtherChannel

Each case contains information such as the case identifier, concept, severity, OSI layer, symptom, topology information, show-command evidence, and expected fault.

### 7. Dashboard

The dashboard provides an overview of troubleshooting activity, including:

- Number of reviewed cases
- Accepted diagnoses
- Edited diagnoses
- Rejected diagnoses
- Case severity distribution
- Issue category distribution
- AI-human agreement
- Recent troubleshooting cases

The project also includes batch testing for running labelled cases through the rule-checking and AI diagnosis pipeline.

## System Workflow

The overall workflow is:

```text
Packet Tracer / Lab Problem
          |
          v
Symptom + Topology Note + Show-Command Evidence
          |
          v
Deterministic Python Rule Checker
          |
          v
AI-Assisted Diagnosis
          |
          v
Root Cause + Evidence + Next Command + Fix Steps
          |
          v
Human Review
          |
          v
Accept / Edit / Reject
          |
          v
Case Log and Dashboard
```

The workflow keeps the AI involved in the reasoning process while retaining human responsibility for the final diagnosis.

## Project Coverage

The troubleshooting cases represent practical Cisco-style laboratory scenarios, including:

| Category | Example Faults |
|---|---|
| VLAN | Incorrect access VLAN, missing allowed VLAN |
| IP Addressing | Incorrect gateway, subnet mask errors, duplicate IP |
| DHCP | Missing pool configuration, unavailable addresses |
| DNS | Incorrect DNS server, failed name resolution |
| Routing | Missing routes, OSPF adjacency problems |
| NAT/ACL | Incorrect NAT configuration, ACL restrictions |
| Wireless | Authentication and MAC filtering problems |
| Physical | Administratively down interface |
| Layer-2 Infrastructure | Switching loops, port security, EtherChannel mismatch |

## Evaluation

The project includes human review of AI-generated troubleshooting diagnoses.

The report records 83 diagnostic sessions with the following review outcomes:

| Review Outcome | Sessions | Share |
|---|---:|---:|
| Accepted | 66 | 79.5% |
| Edited | 6 | 7.2% |
| Rejected | 11 | 13.3% |
| Total | 83 | 100% |

Accepted cases represent diagnoses that the reviewer agreed with without modification. Edited cases required corrections, while rejected cases were replaced by the reviewer because the AI diagnosis was not supported by the available evidence.

## Responsible AI Approach

NetSage AI does not allow an AI-generated response to directly modify a router, switch, access point, or other network device.

The system separates:

1. Deterministic configuration checks
2. AI-based interpretation
3. Human decision-making

This design keeps the AI in an advisory role and requires human oversight before a troubleshooting diagnosis is treated as final.

## Technologies and Environment

The project is based on the following technologies and environments documented in the project report:

- Python
- Artificial Intelligence
- Cisco Packet Tracer
- Cisco networking concepts and show-command evidence
- Rule-based diagnosis
- AI-assisted diagnosis
- Dashboard-based evaluation
- Labelled troubleshooting dataset

The specific language-model service is configured as part of the application and is dependent on the availability of the configured language-model service.

## Project Structure

A typical project organization can contain the following components:

```text
NetSage-AI/
|
|-- README.md
|-- application/
|   |-- main application files
|
|-- dataset/
|   |-- troubleshooting cases
|
|-- rules/
|   |-- deterministic rule checker
|
|-- prompts/
|   |-- AI diagnosis prompts
|
|-- dashboard/
|   |-- dashboard components
|
|-- logs/
|   |-- human review and responsible AI records
|
|-- tests/
|   |-- batch testing resources
|
|-- docs/
|   |-- project documentation
|
```

The exact repository structure may differ depending on the implementation.

## Usage Workflow

A user can use the system by following these general steps:

1. Open the NetSage AI application.
2. Enter the observed network symptom.
3. Provide the relevant topology information.
4. Add the available show-command output.
5. Select the appropriate category and severity.
6. Run the deterministic rule checker.
7. Submit the case for AI-assisted diagnosis.
8. Review the generated root cause, evidence, next command, and fix steps.
9. Accept, edit, or reject the diagnosis.
10. Use the dashboard to review stored troubleshooting results.

## Limitations

NetSage AI is intended for Cisco Packet Tracer and laboratory-style troubleshooting rather than unrestricted production network diagnosis.

The deterministic rule checker focuses on common configuration mistakes and does not reproduce the complete behaviour of Cisco IOS or a complete network management platform.

The quality of the AI recommendation also depends on the quality and completeness of the provided symptom, topology information, and command output.

The AI component depends on the availability and response of the configured language-model service. Therefore, deterministic checks and human review remain important components of the system.

## Project Outcome

NetSage AI demonstrates a practical application of AI to network troubleshooting in a controlled laboratory environment. The project combines a labelled troubleshooting dataset, deterministic configuration checks, structured AI reasoning, human review, and dashboard-based monitoring into a single workflow.

The primary contribution of the project is assisted diagnosis rather than autonomous network configuration. By requiring the AI to use available evidence and keeping a human reviewer responsible for the final decision, the system provides a controlled approach to applying generative AI to networking education.

## Academic Information

**Project Title:** NetSage AI: AI-Assisted Troubleshooting Helper for Cisco Packet Tracer Labs

**Program:** B.Tech Computer Science and Engineering

**Institution:** KIIT Deemed to be University, Bhubaneswar, Odisha

**Program:** Cisco AICTE Virtual Internship Program 2026 (AI Domain)

**Project Members:**
- Moumita Das — Roll No. 23051118
- Sayanika Upadhyay — Roll No. 23051297
- Sambuddha Chakrabarti — Roll No. 23051779

**Guidance:**
- Prof. Anshu Kumar
- Prof. Debashree Mishra

## References

1. Cisco Networking Academy, CCNA: Introduction to Networks (ITN), Cisco, 2024.
2. Cisco Systems, Inc., Cisco Packet Tracer, Cisco Networking Academy.
3. Cisco Systems, Inc., CCNA Certification Guide: Sample Command-Lines—Verification and Troubleshooting, Cisco, 2025.
4. E. Tabassi, Artificial Intelligence Risk Management Framework (AI RMF 1.0), NIST AI 100-1, National Institute of Standards and Technology, January 2023.

## Disclaimer

NetSage AI is an academic and educational prototype intended to support learning and troubleshooting practice in laboratory environments. AI-generated diagnoses should be reviewed by a qualified human before any network configuration change is made.
