from conflict_interface.utils import JsonMappedClass


class GameObject(JsonMappedClass):
    """
    GameObject extends JsonMappedClass to include a reference
    to the central game instance, allowing subclasses to
    interact with game-wide data.
    """

    def __init__(self, game=None):
        """
        Initializes the GameObject with an optional reference
        to the game instance.

        Args:
            game (optional): The central game instance or None.
        """
        self.game = game  # Reference to the central game instance

    @classmethod
    def from_dict(cls, obj: dict, game=None):
        """
        Create a GameObject (or subclass) from a dictionary,
        and include the game reference.

        Args:
            obj (dict): The dictionary representation of the object.
            game (optional): The central game instance to associate with this object.

        Returns:
            GameObject: An instance of the class.
        """
        # Create the object using the base JsonMappedClass logic
        instance = super().from_dict(obj)
        # Attach the provided game instance
        instance.game = game
        return instance
