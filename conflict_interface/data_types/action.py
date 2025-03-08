from conflict_interface.data_types.game_object import GameObject


class Action(GameObject):
    language = "en"
    action_request_id = ""

    MAPPING = {
        "language": "language",
        "action_request_id": "requestID"
    }