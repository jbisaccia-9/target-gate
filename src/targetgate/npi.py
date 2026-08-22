"""NPI checksum validation.

A National Provider Identifier is 10 digits with a Luhn check digit computed
over the constant prefix 80840 + the first nine digits. That makes identifier
validity COMPUTABLE - a target list containing an NPI that fails its own
checksum contains a typo or a fabrication, and the gate refuses it.

Synthetic identifiers in this repo start with 9, outside the issued range, so
they pass the checksum while being structurally incapable of matching a real
provider.
"""


def luhn_check_digit(first9):
    digits = [int(c) for c in "80840" + first9]
    total = 0
    # Double every second digit from the right (of the 14-digit payload).
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - total % 10) % 10


def valid(npi):
    s = str(npi)
    return len(s) == 10 and s.isdigit() and int(s[9]) == luhn_check_digit(s[:9])


def synthetic(seed_int):
    """Deterministic, checksum-valid, non-issuable NPI (leading 9)."""
    first9 = "9" + str(seed_int).zfill(8)[:8]
    return first9 + str(luhn_check_digit(first9))
