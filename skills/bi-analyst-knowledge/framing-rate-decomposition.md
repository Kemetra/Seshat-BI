# Framing card: rate decomposition

**Card id**: `rate-decomposition`

## Question shape

"A headline moved -- which underlying factor drove it?" Decomposes a top-line
total into the driver rates that multiply to it, so the owner acts on the
RIGHT lever. The specific factors (e.g. a price x volume x frequency split, or
whatever the approved contracts support) are domain-dependent and come from the
contracts, never assumed here; sustained domain walkthroughs live in the
examples.

## Required inputs

- A headline measure that factors into driver rates via APPROVED contracts
  only (e.g. a total = a count x an average; an average = a total / a count).
  The factors must each be an approved measure or a trivially-derived ratio of
  approved measures. If a factor is not backed by a contract, it is a [GAP].
- The dimension(s) over which to attribute the move (usually time or segment).

## Visual guidance

- Show the headline and its factors together so the reader sees which factor
  moved -- small multiples, or a factor-delta view over time.
- Decompose only into factors the data supports; do not invent a factor to
  complete a textbook identity.

## Statistical guardrail (signal vs noise)

- Each factor is an approved measure or a labeled ratio of approved measures
  -- never a new metric coined to make the decomposition tidy.
- **Attribution honesty**: two factors moving in opposite directions can leave
  the headline flat; report each factor's move, not just the net.
- Correlation is not causation: "volume drove sales" is an ARITHMETIC
  decomposition (volume x price = sales), not a causal claim about why volume
  moved. State it as decomposition, not cause.

## So-what template

"<headline> moved <+/-X%>; decomposed, <factor A> <+/-a%> and <factor B>
<+/-b%> -- the move is mostly <factor>, so the lever is <that factor's
domain meaning per its contract>."
