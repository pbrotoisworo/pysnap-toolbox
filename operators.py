# Tools related to SNAP operators

def operator_source_flags(operator: str):
    """
    Handle edge cases for operators containing different
    flags which indicate file source

    Parameters
    ----------
    operator: str
        SNAP Operator as identified in the SNAP Graphs
    """

    unique_cases = {
        "Interferogram": "SsourceProduct",
        "TopoPhaseRemoval": "SsourceProduct",
        "GoldsteinPhaseFiltering": "SsourceProduct",
        "Subset": "PinputFile"  # Workaround for bug. Using XML graph file
    }

    if not unique_cases.get(operator):
        return "Ssource"
    return unique_cases.get(operator)

def default_operator_suffix(operator: str, **kwargs) -> str:
    """
    Function imitates the default string that is usually appended to output filenames
    after using an operator as seen in SNAP.

    Parameters
    ----------
    operator: str
        SNAP Operator as identified in the SNAP Graphs
    kwargs: dict
        Keyword arguments that include some arguments which might be necessary
        for certain SNAP operators
    """
    if operator == "TOPSAR-Split":
        if not kwargs.get("subswath"):
            raise ValueError("TOPSAR-Split needs a subswath kwarg")
        return kwargs.get("subswath")
    elif operator == "BandSelect":
        if not kwargs.get("band_suffix"):
            raise ValueError("BandSelect needs a band_suffix kwarg")
        return kwargs.get("band_suffix")

    suffix_dict = {
        "TOPSAR-Split": None,
        "BandSelect": None,
        "SnaphuExport": "",
        "SnaphuUnwrapping": "",  # custom operator
        "Apply-Orbit-File": "Orb",
        "Back-Geocoding": "Stack",
        "Interferogram": "Ifg",
        "TOPSAR-Deburst": "Deb",
        "TopoPhaseRemoval": "Topo",
        "Coherence": "Coh",
        "Multilook": "ML",
        "GoldsteinPhaseFiltering": "Flt",
        "Subset": "Subset",
        "Terrain-Correction": "TC",
        "SnaphuImport": "Unw",
        "Import-Vector": "Vec",
        "Land-Sea-Mask": "Msk"
    }

    out = suffix_dict.get(operator)
    if out is None:
        raise ValueError(f"Operator '{operator}' not recognized as a valid SNAP Graph operator")
    return out

if __name__ == "__main__":
    pass
