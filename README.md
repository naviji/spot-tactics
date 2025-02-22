# spot-tactics

TODO:
- Modify pin find logic to recognize relative pins
- Moving into danger even if the best move of the opponent is not to take it is still a sacrifice
- Classify mate in <= 10 moves
- Add test for fork detection via xrays
- Think about tactics arising from an unplayed move


OBSERVATIONS:
Lichess puzzles only show when we reach a winning position, not when we miss moves that are good, but our position is still terrible
Fork logic didnt' consider forks done by king
Hanging pieces doesn't consider pieces that can be exchanged for gain of material
Pin logic only considers absolute pins to the king
Simpler sacrifice logic, even if the opponent's best move is not to capture, it's still a sacrifice

Information:

A decoy is when you force an enemy piece to move to set up a tactic.

It's attraction if you care that the piece moves to a particular square, for example if something bad will happen to it on that square. 

It's deflection (also called distraction) if you care that the piece moves away from the square it's currently on, for example if it's guarding something important.

My favorite type of tactic in chess is "deflecting the checking piece"!