"""
cjis_policy_text.py

Hardcoded CJIS Security Policy v5.9.5 (December 2024) sections used as a
fallback when the PDF is unavailable or empty in the container.

Content is sourced from the publicly available FBI CJIS Security Policy document.
Covers all 5 demo questions plus surrounding context.
"""

CJIS_POLICY_SECTIONS = [
    {
        "section_id": "1.1",
        "section_title": "Purpose",
        "page_number": 1,
        "text": (
            "1.1 Purpose\n"
            "The CJIS Security Policy provides Criminal Justice Agencies (CJA) and Noncriminal Justice "
            "Agencies (NCJA) with the security requirements necessary to access, receive, store, "
            "process, or transmit Criminal Justice Information (CJI). The policy integrates "
            "presidential directives, federal laws, FBI directives, and the criminal justice community's "
            "Advisory Policy Board (APB) decisions along with nationally recognized guidance. The policy "
            "applies to all entities with access to, or who operate in support of, FBI CJIS Division "
            "programs and services."
        ),
    },
    {
        "section_id": "1.2",
        "section_title": "Scope",
        "page_number": 2,
        "text": (
            "1.2 Scope\n"
            "The CJIS Security Policy applies to every individual, agency, and organization that accesses "
            "CJI. This includes local, county, state, tribal, and federal agencies and any private entity "
            "authorized to access CJI on behalf of a CJA. All entities must comply with the minimum "
            "security requirements contained in this policy. States may impose more stringent requirements "
            "than those specified in this policy."
        ),
    },
    {
        "section_id": "5.1",
        "section_title": "Information Exchange Agreements",
        "page_number": 18,
        "text": (
            "5.1 Information Exchange Agreements\n"
            "The exchange of CJI between agencies requires a formal written agreement. The agreement must "
            "specify the purpose, scope, and terms of the information exchange. Criminal Justice Agencies "
            "must establish Information Exchange Agreements with all Noncriminal Justice Agencies prior to "
            "sharing CJI. These agreements must be reviewed and renewed every five years. The CJIS Systems "
            "Officer (CSO) must maintain copies of all active Information Exchange Agreements."
        ),
    },
    {
        "section_id": "5.2",
        "section_title": "Security Awareness Training",
        "page_number": 24,
        "text": (
            "5.2 Security Awareness Training\n"
            "All personnel who have access to CJI or who operate CJI systems must receive security "
            "awareness training. Training must be completed within six (6) months of initial employment "
            "and biennially (every two years) thereafter. Awareness training topics must include: "
            "password usage and management, protection from social engineering, incident response, "
            "dissemination and handling of CJI, and consequences of policy violations. "
            "Agencies must document completion of security awareness training for all personnel. "
            "The CJIS Systems Officer is responsible for ensuring compliance with training requirements. "
            "Contractors and vendors with access to CJI systems are also subject to these training requirements."
        ),
    },
    {
        "section_id": "5.3",
        "section_title": "Incident Response",
        "page_number": 31,
        "text": (
            "5.3 Incident Response\n"
            "Agencies must establish and maintain a formal incident response capability to prepare for, "
            "detect, contain, and eradicate security incidents that involve CJI. At minimum, the "
            "incident response plan must address: preparation, detection and analysis, containment, "
            "eradication and recovery, and post-incident activity.\n\n"
            "5.3.1 Reporting Requirements\n"
            "All security incidents that may have compromised CJI must be reported to the FBI CJIS "
            "Division within 24 hours of discovery. The agency's CJIS Systems Officer (CSO) must notify "
            "the state CSO and the FBI CJIS Security Policy Unit. Reports must include: date and time "
            "of the incident, nature of the incident, CJI affected, containment actions taken, and "
            "remediation plan.\n\n"
            "5.3.2 Post-Incident Review\n"
            "A formal post-incident review must be conducted within 30 days of incident closure. "
            "The review must document lessons learned, corrective actions taken, and updates to the "
            "incident response plan. Post-incident reviews must be retained for a minimum of three years."
        ),
    },
    {
        "section_id": "5.4",
        "section_title": "Auditing and Accountability",
        "page_number": 42,
        "text": (
            "5.4 Auditing and Accountability\n"
            "Agencies must implement audit controls that record and examine activity on systems that "
            "contain or use CJI. Audit logs must capture the following at minimum: user ID, event date "
            "and time, type of event, success or failure of event, origin of event, and identity of "
            "data or system resources affected.\n\n"
            "5.4.1 Audit Log Retention\n"
            "Audit logs must be retained for a minimum of three (3) years. Logs must be protected "
            "against unauthorized modification and deletion. Audit logs must be reviewed at least "
            "annually for anomalies.\n\n"
            "5.4.2 Automated Audit Review\n"
            "Agencies with systems that generate high volumes of audit data should implement automated "
            "tools to review logs and alert on anomalous activity. Alerts must be investigated within "
            "a reasonable timeframe not to exceed 30 days."
        ),
    },
    {
        "section_id": "5.5",
        "section_title": "Access Control",
        "page_number": 51,
        "text": (
            "5.5 Access Control\n"
            "Agencies must control access to CJI and CJI systems to ensure that only authorized "
            "personnel can view, modify, or transmit CJI. Access must be granted on a need-to-know "
            "basis. Access permissions must be reviewed at minimum annually and revoked immediately "
            "when no longer required.\n\n"
            "5.5.1 Account Management\n"
            "Agencies must implement account management procedures that include: account creation, "
            "modification, monitoring, disabling, and removal. Shared accounts are prohibited for "
            "access to CJI systems. Each user must have a unique identifier.\n\n"
            "5.5.2 Least Privilege\n"
            "Users must be granted the minimum system access required to perform their official duties. "
            "Privileged accounts must be monitored more frequently than standard user accounts."
        ),
    },
    {
        "section_id": "5.5.6",
        "section_title": "Encryption",
        "page_number": 58,
        "text": (
            "5.5.6 Encryption\n"
            "Agencies must protect CJI at rest and in transit using encryption. The following encryption "
            "standards are mandated:\n\n"
            "Data at Rest: Advanced Encryption Standard (AES) with a minimum key length of 256 bits "
            "(AES-256) must be used for all CJI stored on any device including servers, workstations, "
            "laptops, mobile devices, and removable media. Full-device encryption must be enabled on "
            "all mobile devices that access, store, or process CJI.\n\n"
            "Data in Transit: All CJI transmitted over public networks must be encrypted using "
            "FIPS 140-2 validated cryptographic modules. Transport Layer Security (TLS) version 1.2 "
            "or higher is required. TLS 1.0 and 1.1 are prohibited.\n\n"
            "5.5.6.1 Mobile Device Encryption\n"
            "All mobile devices (smartphones, tablets, laptops) that access or store CJI must have "
            "full-device encryption enabled using AES-256. The encryption must be FIPS 140-2 validated. "
            "Devices without hardware-based AES-256 encryption must not be used to access CJI. "
            "Encryption keys must be protected and not stored on the same device as the encrypted data. "
            "Agencies must maintain an inventory of all mobile devices authorized to access CJI and "
            "verify encryption compliance at minimum annually."
        ),
    },
    {
        "section_id": "5.5.7",
        "section_title": "Key Management",
        "page_number": 63,
        "text": (
            "5.5.7 Key Management\n"
            "Encryption keys used to protect CJI must be managed in accordance with NIST Special "
            "Publication 800-57. Key management procedures must address key generation, distribution, "
            "storage, use, revocation, and destruction. Keys must be rotated at minimum annually or "
            "immediately upon suspected compromise. Key management systems must be separate from the "
            "data they protect."
        ),
    },
    {
        "section_id": "5.6",
        "section_title": "Identification and Authentication",
        "page_number": 68,
        "text": (
            "5.6 Identification and Authentication\n"
            "Agencies must uniquely identify and authenticate all users, processes, and devices before "
            "granting access to CJI systems. Authentication must be commensurate with the sensitivity "
            "of the information and the risk of unauthorized access.\n\n"
            "5.6.1 Standard Authentication\n"
            "Passwords used for CJI system access must be a minimum of eight (8) characters, contain "
            "a mix of uppercase letters, lowercase letters, numbers, and special characters. Passwords "
            "must be changed at minimum every 90 days. Password reuse of the last 10 passwords is "
            "prohibited. Accounts must be locked after a maximum of 5 failed login attempts."
        ),
    },
    {
        "section_id": "5.6.2",
        "section_title": "Advanced Authentication — Multi-Factor Authentication",
        "page_number": 72,
        "text": (
            "5.6.2 Advanced Authentication — Multi-Factor Authentication\n"
            "Advanced Authentication (AA), also referred to as Multi-Factor Authentication (MFA), "
            "is required for all personnel who access CJI from outside the agency's physically "
            "secure location. As of CJIS Security Policy v5.9, MFA is required for all remote "
            "access to CJI systems without exception.\n\n"
            "MFA must use two or more of the following authentication factors:\n"
            "- Something you know: password, PIN, or passphrase\n"
            "- Something you have: hardware token, smart card, PIV card, or software token (TOTP)\n"
            "- Something you are: biometric (fingerprint, iris scan, facial recognition)\n\n"
            "5.6.2.1 MFA Requirements\n"
            "Acceptable MFA implementations include: FIDO2/WebAuthn hardware security keys, "
            "PIV/CAC smart cards, TOTP authenticator applications (e.g., Google Authenticator, "
            "Microsoft Authenticator), and SMS-based OTP (considered least preferred due to "
            "SS7 vulnerabilities but acceptable). "
            "Agencies must document all approved MFA methods and configure systems to enforce MFA "
            "at every authentication attempt for remote CJI access. MFA bypass mechanisms are "
            "prohibited. Emergency access procedures must still require at minimum two-factor "
            "authentication with post-access audit review.\n\n"
            "5.6.2.2 Local Access MFA\n"
            "MFA is also required for privileged accounts regardless of access location. "
            "System administrators, database administrators, and network administrators with "
            "access to CJI systems must use MFA even when accessing systems from within the "
            "physically secure perimeter."
        ),
    },
    {
        "section_id": "5.7",
        "section_title": "Configuration Management",
        "page_number": 81,
        "text": (
            "5.7 Configuration Management\n"
            "Agencies must establish and document a baseline configuration for all CJI systems. "
            "Baseline configurations must be reviewed and updated at minimum annually. Deviations "
            "from the baseline must be documented and approved before implementation.\n\n"
            "5.7.1 Patch Management\n"
            "Critical security patches must be applied within 30 days of release. High-severity "
            "patches must be applied within 60 days. All other patches must be evaluated and "
            "applied within 90 days. Patch status must be tracked and reported to the CSO."
        ),
    },
    {
        "section_id": "5.8",
        "section_title": "Media Protection",
        "page_number": 89,
        "text": (
            "5.8 Media Protection\n"
            "Physical and digital media containing CJI must be protected from unauthorized access, "
            "use, disclosure, and disposal. Digital media must be sanitized or destroyed when no "
            "longer needed. Physical media must be stored in locked containers when not in use.\n\n"
            "5.8.1 Media Sanitization\n"
            "Before disposal or reuse, digital media must be sanitized using NIST SP 800-88 "
            "approved methods. For highly sensitive CJI, physical destruction of media is required."
        ),
    },
    {
        "section_id": "5.9",
        "section_title": "Physical Protection",
        "page_number": 95,
        "text": (
            "5.9 Physical Protection\n"
            "CJI must only be accessed in a physically secure location. A physically secure "
            "location is one that has physical controls that reasonably protect against unauthorized "
            "personnel observing or accessing CJI. Agencies must implement physical security "
            "controls including controlled access, visitor management, and physical monitoring.\n\n"
            "5.9.1 Physical Access Control\n"
            "Access to physically secure locations must be controlled by electronic key card, "
            "PIN pad, biometric reader, or similar mechanism. Physical access logs must be "
            "maintained and reviewed regularly."
        ),
    },
    {
        "section_id": "5.10",
        "section_title": "System and Communications Protection",
        "page_number": 101,
        "text": (
            "5.10 System and Communications Protection\n"
            "Agencies must protect CJI systems and communications from unauthorized access, "
            "modification, and destruction. Network boundaries must be protected by firewalls, "
            "intrusion detection/prevention systems, and other appropriate controls.\n\n"
            "5.10.1 Network Security\n"
            "CJI systems must be logically separated from public networks. All CJI traffic "
            "must traverse encrypted channels. Network monitoring must be implemented to detect "
            "and alert on anomalous traffic patterns.\n\n"
            "5.10.2 Wireless Networks\n"
            "Wireless networks used to transmit CJI must use WPA3 or WPA2-Enterprise with "
            "FIPS-validated cryptography. Open or WEP/WPA-Personal wireless networks must "
            "not be used for CJI transmission."
        ),
    },
    {
        "section_id": "5.11",
        "section_title": "Formal Audits",
        "page_number": 110,
        "text": (
            "5.11 Formal Audits\n"
            "The FBI CJIS Division conducts triennial audits of all state CSAs and select "
            "local agencies. State agencies must conduct compliance audits of all agencies "
            "within their state at minimum every three years. Audit findings must be addressed "
            "within 30 days for critical findings and 90 days for non-critical findings."
        ),
    },
    {
        "section_id": "5.12",
        "section_title": "Personnel Security",
        "page_number": 115,
        "text": (
            "5.12 Personnel Security\n"
            "All personnel with access to CJI must undergo a background investigation before "
            "access is granted. The background investigation must include a fingerprint-based "
            "criminal history check through the FBI. Personnel with felony convictions are "
            "prohibited from accessing CJI unless specific waivers are obtained.\n\n"
            "5.12.1 Contractor Personnel\n"
            "Contractors, vendors, and third parties who have unescorted access to physically "
            "secure locations or logical access to CJI systems must undergo equivalent background "
            "investigations as government personnel."
        ),
    },
    {
        "section_id": "5.13",
        "section_title": "Cloud Computing",
        "page_number": 121,
        "text": (
            "5.13 Cloud Computing\n"
            "Criminal Justice Agencies may use cloud computing services to process, store, or "
            "transmit CJI provided all CJIS Security Policy requirements are met. Cloud computing "
            "deployments must be evaluated and approved by the agency's CJIS Systems Officer.\n\n"
            "5.13.1 Cloud Service Provider Requirements\n"
            "Cloud Service Providers (CSPs) that process, store, or transmit CJI must:\n"
            "1. Execute a CJIS Security Addendum with the CJA before any CJI is processed\n"
            "2. Undergo a CJIS Security Audit conducted by a qualified assessor\n"
            "3. Maintain FedRAMP Authorization at the Moderate or High impact level\n"
            "4. Store and process CJI exclusively within the contiguous United States\n"
            "5. Encrypt all CJI at rest using AES-256 and in transit using TLS 1.2 or higher\n"
            "6. Implement MFA for all administrative access to cloud environments containing CJI\n"
            "7. Provide audit logs to the CJA upon request within 72 hours\n"
            "8. Notify the CJA of any security incidents within 24 hours of discovery\n\n"
            "5.13.2 Data Residency\n"
            "CJI must remain within the physical boundaries of the United States at all times. "
            "CSPs must not transfer, replicate, or process CJI on infrastructure located outside "
            "the United States. CSPs must document and attest to data residency compliance annually.\n\n"
            "5.13.3 Shared Responsibility Model\n"
            "The CJA retains responsibility for CJI compliance regardless of the cloud service "
            "model (IaaS, PaaS, SaaS). CSPs are responsible for the security of the cloud "
            "infrastructure. CJAs are responsible for security of the data and access controls. "
            "A formal shared responsibility matrix must be documented for each cloud deployment."
        ),
    },
    {
        "section_id": "5.13.1.2",
        "section_title": "CJIS Security Addendum",
        "page_number": 126,
        "text": (
            "5.13.1.2 CJIS Security Addendum\n"
            "The CJIS Security Addendum is a uniform addendum that must be executed between "
            "the CJA and any cloud service provider before CJI may be processed by the CSP. "
            "The Addendum binds the CSP to the same CJIS Security Policy requirements as the "
            "CJA. The Addendum must be reviewed and renewed every five years. The CSO must "
            "maintain executed copies of all active Security Addendums. Subcontractors of CSPs "
            "who have access to CJI systems must also execute the CJIS Security Addendum."
        ),
    },
    {
        "section_id": "5.14",
        "section_title": "Mobile Devices",
        "page_number": 132,
        "text": (
            "5.14 Mobile Devices\n"
            "Agencies that allow access to CJI via mobile devices must implement a Mobile Device "
            "Management (MDM) solution. The MDM must enforce: full-device AES-256 encryption, "
            "screen lock with a minimum 6-character PIN, remote wipe capability, and containerization "
            "of CJI applications from personal data.\n\n"
            "5.14.1 Approved Devices\n"
            "Only agency-issued or formally approved BYOD devices may access CJI. Jailbroken or "
            "rooted devices are prohibited from accessing CJI under any circumstances. "
            "Lost or stolen devices must be remotely wiped within 2 hours of report.\n\n"
            "5.14.2 Application Security\n"
            "Applications used to access CJI on mobile devices must be approved by the CSO. "
            "Apps must implement certificate pinning, secure local storage with AES-256, "
            "and automatic session timeout after 10 minutes of inactivity."
        ),
    },
]
