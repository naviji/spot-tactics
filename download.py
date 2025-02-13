import berserk
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Get API token
API_TOKEN = os.getenv("LICHESS_API_TOKEN")

# Create Lichess client
session = berserk.TokenSession(API_TOKEN)
client = berserk.Client(session=session)

print("Lichess API client initialized successfully!")

# Define username and output file
username = "kramford"
output_file = f"{username}_games.pgn"

# Open file in write mode
with open(output_file, "w", encoding="utf-8") as f:
    for game in client.games.export_by_player(username, as_pgn=True, analysed=True, evals=True):
        f.write(game + "\n\n")  # Write each game followed by a newline

print(f"Games saved to {output_file} successfully!")


