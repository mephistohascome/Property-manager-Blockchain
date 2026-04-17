"""Map property-registry security issues to control references."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControlMapping:
    iso_27001: tuple[str, ...]
    nist_csf: tuple[str, ...]
    pci_dss: tuple[str, ...]
    default_remediation: str


CONTROL_MAP: dict[str, ControlMapping] = {
    "forged_document_hash": ControlMapping(
        iso_27001=("A.5.23", "A.8.15"),
        nist_csf=("DE.CM-7", "PR.DS-6"),
        pci_dss=("10.2", "10.3"),
        default_remediation="Validate notarized document digests before invoking the transfer contract.",
    ),
    "missing_multisig_approval": ControlMapping(
        iso_27001=("A.5.3", "A.5.15", "A.5.16"),
        nist_csf=("PR.AA-3", "PR.AC-4"),
        pci_dss=("7.2", "8.4.2"),
        default_remediation="Require multi-party approval from registrar, surveyor, and legal verifier wallets.",
    ),
    "privileged_registry_override": ControlMapping(
        iso_27001=("A.8.2", "A.8.18"),
        nist_csf=("PR.AA-5", "DE.CM-5"),
        pci_dss=("7.2.5", "10.4.1"),
        default_remediation="Remove direct database write privileges and force all title updates through signed smart contracts.",
    ),
    "weak_wallet_hygiene": ControlMapping(
        iso_27001=("A.5.17", "A.8.24"),
        nist_csf=("PR.AA-1", "PR.DS-1"),
        pci_dss=("8.3.6", "3.6.1"),
        default_remediation="Store signing keys in HSM-backed wallets and enforce phishing-resistant MFA for operators.",
    ),
    "orphan_block_validation": ControlMapping(
        iso_27001=("A.8.15", "A.8.16"),
        nist_csf=("DE.CM-1", "PR.PS-4"),
        pci_dss=("10.5.1", "10.7"),
        default_remediation="Alert on block-sequence gaps and quarantine untrusted validator output for manual review.",
    ),
    "missing_offchain_backup": ControlMapping(
        iso_27001=("A.5.30", "A.8.13"),
        nist_csf=("PR.IR-1", "RC.RP-1"),
        pci_dss=("12.10.1", "12.10.2"),
        default_remediation="Replicate notarized evidence and title documents into immutable off-chain backup storage.",
    ),
    "suspicious_transfer_velocity": ControlMapping(
        iso_27001=("A.5.7", "A.8.16"),
        nist_csf=("DE.AE-1", "DE.CM-9"),
        pci_dss=("10.6", "12.10.7"),
        default_remediation="Rate-limit repeat title transfers and require fraud-team review for rapid ownership churn.",
    ),
}


def map_finding(finding_type: str) -> ControlMapping:
    return CONTROL_MAP.get(
        finding_type,
        ControlMapping(
            iso_27001=("A.5.1",),
            nist_csf=("GV.OC-1",),
            pci_dss=("12.1",),
            default_remediation="Document risk owner and remediation plan; align to org security standard.",
        ),
    )


def refs_as_csv(mapping: ControlMapping) -> tuple[str, str, str]:
    return (
        ", ".join(mapping.iso_27001),
        ", ".join(mapping.nist_csf),
        ", ".join(mapping.pci_dss),
    )
