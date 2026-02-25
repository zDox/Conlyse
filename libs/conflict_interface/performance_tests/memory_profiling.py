import gc
import logging
import operator

from pympler import asizeof
from pympler import muppy
from pympler import summary
from pympler import tracker

from examples.helper_functions import load_credentials

# Initialize a memory tracker
tr = tracker.SummaryTracker()


# Function to print sorted summary
def print_memory_summary(title):
    print(f"\n{title}")
    print("-" * 100)
    all_objects = muppy.get_objects()
    sum_data = summary.summarize(all_objects)
    sorted_data = sorted(sum_data, key=operator.itemgetter(2), reverse=True)

    print(f"{'Type':<80} {'Count':>10} {'Size':>12}")
    print("-" * 100)
    for row in sorted_data[:10]:  # Top 10 only for brevity
        obj_type, count, size = row
        if size > 1024:  # Filter small objects
            formatted_size = f"{size / 1024:.2f} KB"
            print(f"{str(obj_type):<80} {count:>10} {formatted_size:>12}")


# Baseline memory usage
print_memory_summary("Baseline Memory Usage")

# Simulate some work in your app (replace this with your actual code)
# Example: Assume this is where your game loop or data loading happens
from conflict_interface import HubInterface

username, password, email, proxy_url = load_credentials()

from conflict_interface.logger_config import setup_library_logger
setup_library_logger(logging.DEBUG)
interface = HubInterface()
interface.login(username, password)

game = interface.join_game(9709963)
research_type = game.get_research_type(2300)
next_research = game.get_research_type(research_type.get_replacing_research())
# Print memory changes after running your code
print_memory_summary("After Running Code")

# Force garbage collection and check again
gc.collect()
print_memory_summary("After Garbage Collection")

# Get the size of the object in bytes
size_in_bytes = asizeof.asizeof(game)

# Convert to human-readable format
def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024

print(f"Size of the object: {format_size(size_in_bytes)}")