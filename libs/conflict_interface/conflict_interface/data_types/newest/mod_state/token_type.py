from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..mod_state.configuration import ConsumptionStrategyConfig
from ..mod_state.configuration import DurationStrategyConfig
from ..mod_state.configuration import EffectScalingStrategyConfig
from ..mod_state.configuration import EffectsConfig
from ..mod_state.configuration import MergeStrategyConfig
from ..mod_state.configuration import PurchaseStrategyConfig
from ..mod_state.configuration import RenderConfig
from ..mod_state.configuration import SplitStrategyConfig
from ..mod_state.configuration import TokenClassConfig
from ..mod_state.configuration import TokenPriorityConfig
from ..mod_state.configuration import VisibilityStrategyConfig


from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class TokenType(GameObject):
    C = "ultshared.modding.types.UltTokenType"
    item_id: int
    duration_strategy: DurationStrategyConfig
    token_class: TokenClassConfig
    priority: TokenPriorityConfig
    split_strategy: SplitStrategyConfig
    effects_config: EffectsConfig
    purchase_strategy: PurchaseStrategyConfig
    merge_strategy: MergeStrategyConfig
    visibility_strategy: VisibilityStrategyConfig
    token_name: str
    token_description: str
    effect_scaling_strategy: EffectScalingStrategyConfig
    consumption_strategy: ConsumptionStrategyConfig
    render_config: RenderConfig
    token_display: str

    MAPPING = {
        "item_id": "itemID",
        "duration_strategy": "durationStrategy",
        "token_class": "tokenClass",
        "priority": "priority",
        "split_strategy": "splitStrategy",
        "effects_config": "effects",
        "purchase_strategy": "purchaseStrategy",
        "merge_strategy": "mergeStrategy",
        "visibility_strategy": "visibilityStrategy",
        "token_name": "tokenName",
        "token_description": "tokenDesc",
        "effect_scaling_strategy": "effectScalingStrategy",
        "consumption_strategy": "consumptionStrategy",
        "render_config": "renderConfig",
        "token_display": "tokenDisplay",
    }