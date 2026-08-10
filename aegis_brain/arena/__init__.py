"""The Optimus Portfolio Arena — hundreds of portfolios, frozen before scoring.

Murat asked for "hundreds of portfolios ... backtest with real or made up data
to test itself and learn". That is a good instinct and, run naively, it is the
overfitting machine this entire programme exists to prevent: generate, look,
tweak, look again, and eventually something wins by construction.

The Arena keeps the aggressive search and removes the part that lies:

  1. Every genome is generated from the SIGNAL REGISTRY, so a closed mechanism
     cannot enter the search at all.
  2. All genomes are FROZEN into a manifest, with a content hash, BEFORE the
     first return is computed. The manifest records the full denominator.
  3. Every loser is preserved. A genome that is never mentioned again still
     counts against every survivor's significance.
  4. Two venues that never mix: SYNTHETIC worlds where we planted the answer
     and can therefore score the Arena itself, and REAL point-in-time history
     where we can score a strategy. Synthetic profit is never evidence of
     alpha, and the report keeps them in separate sections.
  5. Post-result mutation is a NEW generation with its own manifest, its own
     denominator and its parent recorded.
"""
