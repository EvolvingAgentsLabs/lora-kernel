# P16 — a guard on the region's edge that does not ask the model how it feels

**The problem this attacks.** P14 measured that an expert's formulas fall from
**30/30 inside its region to 1/20 outside**, and that **nothing in its output marks
the difference**: same numbered structure, same confidence, invented physics
**[ran]**. Asking a model for its confidence is the obvious guard and it is the one
P14 ruled out.

**The idea.** The *behaviour of the tool layer* might separate what the model's
prose does not. Outside its region the expert names quantities it does not
understand, and the tool layer has to turn those names into calls. If the rate of
rejected calls, or the number of steps, or the shape of the chain shifts, then a
guard exists that never consults the model's opinion of itself.

**It costs nothing.** P13 and P14 already recorded every transcript, every call and
every rejection, in region and out. This is arithmetic over files on disk.

## The signals, listed before any of them is computed

Searching a set of already-seen records for whichever number happens to separate
them is how a measurement becomes a search. So the list is fixed here, **all six
are reported whatever they say**, and none of them is a result on its own.

| # | signal | why it might shift outside the region |
|---|---|---|
| 1 | tool calls per case | an expert out of its depth may over- or under-ask |
| 2 | rejected calls per case | labels it does not understand should be harder to turn into valid calls |
| 3 | rejection rate (rejected / calls) | the same, normalised for chain length |
| 4 | numbered steps per case | a chain it cannot plan may run long or stop short |
| 5 | chains with no evaluable step at all | prose instead of arithmetic |
| 6 | transcript length | a coarse proxy for the above, included to see if the subtler ones add anything |

## What would count, and what would not

**Counts:** a signal whose in-region and out-of-region distributions separate well
enough that a single threshold classifies most cases correctly — reported with the
threshold, the accuracy, and the sample size.

**Does not count:** any signal that only separates on one of the two arms, or that
needs a threshold fitted per arm. That is a coincidence with a number attached.

**And nothing here is a result yet, whatever it shows.** The signals are being
chosen with the answers already visible. A separation found this way is a
**hypothesis**, and it has to be confirmed on families neither P13 nor P14 used
before it can guard anything.

**Sample sizes are small and stated up front**: 30 cases in region and 20 out, per
arm. A threshold fitted on 50 points is not a detector.
