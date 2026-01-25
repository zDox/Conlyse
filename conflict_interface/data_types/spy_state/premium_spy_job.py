from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class PremiumSpyJob(GameObject):
    """
    Abstract class for premium spy jobs
    """
    mission: int
    country_wide: bool
    province_id: int
    spy_owner_id: int
    amount: int
    time: int
    premium: bool
    day: int
    opponent_id: int
    name: str
    max_gm_limit_level: int
    description: str
    premium_id: int
    job_name: str

    MAPPING = {
        "mission": "mission",
        "country_wide": "countrywide",
        "province_id": "provinceID",
        "spy_owner_id": "spyOwnerID",
        "amount": "amount",
        "time": "time",
        "premium": "premium",
        "day": "day",
        "opponent_id": "opponentID",
        "name": "name",
        "max_gm_limit_level": "maxGmLimitLevel",
        "description": "description",
        "premium_id": "premiumID",
        "job_name": "jobName"
    }


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class RevealProvinceArmiesJob(PremiumSpyJob):
    """
    Reveal province armies job
    """
    C = "ultshared.spyjobs.UltRevealProvinceArmiesJob"

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class CountryInfoJob(PremiumSpyJob):
    """
    Country info job
    """
    C = "ultshared.spyjobs.UltCountryInfoJob"

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class DecreaseMoralJob(PremiumSpyJob):
    """
    Decrease moral job
    """
    C = "ultshared.spyjobs.UltDecreaseMoralJob"

    start_moral: int

    MAPPING = {
        **PremiumSpyJob.MAPPING,
        "start_moral": "startMorale",
    }

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class DestroyResouceJob(PremiumSpyJob):
    """
    Destroy resource job
    """
    C = "ultshared.spyjobs.UltDestroyResourceJob"

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class DamageUpgradeJob(PremiumSpyJob):
    """
    Damage upgrade job
    """
    C = "ultshared.spyjobs.UltDamageUpgradeJob"

    damaged_upgrade: int

    MAPPING = {
        **PremiumSpyJob.MAPPING,
        "damaged_upgrade": "damagedUpgrade",
    }

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class RevealAllArmiesJob(PremiumSpyJob):
    """
    Reveal all armies job
    """
    C = "ultshared.spyjobs.UltRevealAllArmiesJob"