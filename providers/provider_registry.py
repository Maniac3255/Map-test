"""Registry of enabled outage provider adapters."""

from providers import duke_energy

# Future provider imports:
# from providers import (
#     xcel_energy,
#     alabama_power,
#     first_energy,
# )


ENABLED_PROVIDERS = [
    duke_energy,

    # Enable these after their provider files are created:
    # xcel_energy,
    # alabama_power,
    # first_energy,
]
