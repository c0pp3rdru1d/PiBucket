from __future__ import annotations

from pathlib import Path


def _norm_mac(mac: str) -> str:
    return mac.strip().lower().replace("-", ":").replace(".", ":")


class VendorLookup:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    @classmethod
    def from_manuf(cls, path: Path) -> "VendorLookup":
        mapping: dict[str, str] = {}
        if not path.exists():
            return cls(mapping)

        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            prefix, vendor = parts[0], parts[1].strip()
            prefix = prefix.split("/")[0]
            prefix = _norm_mac(prefix)
            toks = prefix.split(":")
            if len(toks) < 3:
                continue
            oui = ":".join(toks[:3])
            mapping.setdefault(oui, vendor)
        return cls(mapping)

    def vendor_for(self, mac: str | None) -> str | None:
        if not mac:
            return None
        mac = _norm_mac(mac)
        toks = mac.split(":")
        if len(toks) < 3:
            return None
        return self.mapping.get(":".join(toks[:3]))

