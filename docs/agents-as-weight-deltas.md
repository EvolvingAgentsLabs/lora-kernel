# Agents as weight deltas, and the metric that does not measure what it looks like

*On speculative decoding, a pool of small experts, and a beautiful idea that
turned out to select for the wrong thing.*

---

Ismael Faro suggested I go and study speculative decoding, and see what it could
be used for.

The suggestion was right in the way good suggestions usually are: not because the
obvious use worked, but because studying it carefully produced a better question
than the one I started with. This is what I found, in the order I found it,
including the part where the idea I was most excited about stopped being
available.

## The idea

Speculative decoding makes inference faster by having a small model guess ahead.
A **drafter** proposes a handful of tokens; the big **target** checks all of them
in one forward pass instead of one at a time; the ones that survive are kept. You
get several tokens for the price of one pass.

Separately, vLLM can hold many LoRA adapters over a single resident base model
and serve them in the same batch. One base, many small deltas, no extra models in
memory.

Put those two together and something very appealing falls out.

If experts are just adapters, and drafting is just guessing ahead, then **let
several experts draft at once**. Run three or four domain adapters in parallel on
the same context, let each propose a short continuation, verify all the branches
in one pass with tree attention, and keep the branch the target accepted most.

Routing — the perennially annoying "which agent should handle this?" problem that
normally costs an extra model call and a classifier nobody trusts — would become
**free**. Not cheap: free. The tokens were already generated. The verification
pass was already going to happen. The winner falls out of arithmetic you were
paying for anyway.

And then the whole system collapses into something almost embarrassingly simple.
The harness — tool syntax, action tokens, state transitions — is another adapter.
The experts are adapters. The router is a property of the forward pass. Memory is
markdown in git, because a weight delta is not something a person can read. The
evolution loop trains new adapters from traces overnight and drops the ones that
lose.

**Every agent is a weight delta.** The multi-agent system stops being Python
orchestrating API calls and becomes a single model with a pool of small
personalities competing in the arithmetic.

I spent a while enjoying this. It is a genuinely elegant architecture.

## The objection

Speculative decoding has one property that is not a footnote. It is the entire
reason anyone uses it:

> **The output is distribution-preserving.** Rejection sampling is constructed so
> that the accepted tokens are distributed *exactly* as the target model would
> have emitted them.

That is the guarantee. It is why you are allowed to put a small sloppy model in
front of a big careful one and not worry: the small model can only make the
answer arrive sooner, never make it different.

Read that again with the routing idea in mind.

**The drafter cannot change the answer.** If the experts are drafters and the
target is the shared base model, then whatever those experts know, the tokens
that come out are the *base model's* tokens. The legal adapter's legal knowledge
does not reach the output. It arrives faster. It arrives identical.

And the metric is worse than useless — it is inverted. Acceptance rate measures
how often the drafter guessed what the target was going to say. It is a
similarity statistic between drafter and target. Fine-tuning an adapter moves its
distribution *away* from the base; that is what fine-tuning **is**. So:

```
argmax over experts of  acceptance rate against the base
   =  the expert that has drifted least from the base
   =  the least specialised adapter in the pool
```

The tournament, run exactly as designed, is a machine for selecting the expert
that learned the least.

This is not a subtle point once you see it, and the literature is not coy about
it either. There is already a paper formalising drafter selection among multiple
drafters — *Not-a-Bandit*, a no-regret treatment of exactly this choice. It
optimises **speed**. Nobody claims acceptance rate tracks quality, because under
the guarantee above, quality is a constant.

There is a second, more ordinary correction. When I checked whether you could
even do this today, the answer was no: vLLM serves many adapters over one
*target*, but speculative decoding still wants a separate fully-trained draft
model per domain. LoRA-as-drafter is an open RFC, filed three weeks ago. An
earlier attempt applied the adapter to the target and switched it off on the
draft. The architecture I was sketching as "totally viable today" was a proposal
with an issue number.

## What survives

Here is why this is a good outcome rather than a dead end.

The objection kills **one mechanism**. It leaves the thesis standing, and it
turns a large architecture into a small, cheap, decidable question.

Three routes remain. Only the third is interesting.

You can **accept losslessness** and sell what it actually gives you: many experts
on one base, served cheaply and fast. That is real and it ships. It is also not a
capability claim, and it should stop being sold as one.

You can **break losslessness on purpose** — put the domain adapter on the
*target*, so the tokens really are the expert's. That is a correct architecture.
It just costs a verification pass per candidate, and the free routing is gone. If
you want the expert's answer, you pay for the expert's forward pass. There is no
version of this where you get specialist output from generalist arithmetic.

Or you can **keep acceptance rate — but demote it from verdict to signal**, and
ask an empirical question the mechanism does not settle either way:

> Does a drafter's acceptance rate carry *any* information about whether its
> expert would have produced a better answer?

The mechanism says the expert's knowledge cannot reach the output. It does not
say the agreement is meaningless. A drafter and a target that agree are, in some
loose sense, representing the problem the same way — and "this expert already
thinks like the model that will judge it" might be worth something as a hint,
even though it is worthless as a verdict.

I genuinely do not know which way that goes. Which is the point: it is a
hypothesis with a plausible null, and those are the only ones worth building an
instrument for.

## The experiment, and the condition that kills it

Take a task distribution with **demonstrated headroom** — checked first, because
a base model already at the ceiling makes every expert tie, and a tie looks
exactly like a success. Then, over `n` domain adapters:

1. Measure each adapter's acceptance rate as a drafter against the base.
2. Measure each adapter's **verified task score** when it is on the *target*, so
   its knowledge actually reaches the output.
3. Rank both ways. Compare the rankings.

**If they are uncorrelated, routing-by-acceptance is dead** and I will say so in
the README. That is a week of work to settle a question that would otherwise sit
under four subsystems.

## Why this is the right shape for a project

Two of the three legs hold on their own, and both have baselines that are
*ours* rather than convenient.

The **harness as an adapter** — moving tool protocol out of the system prompt and
into weights — is testable now. But the baseline is not "giant JSON schemas",
which is the comparison that would flatter it. It is our own previous result:
binding tools per phase already took peak schema overhead from 5,548 tokens to
817, a reduction of 85%, with no training at all. A harness adapter has to beat
that, on tokens *and* on malformed-call rate, where the incumbent is
grammar-constrained decoding — which does not make bad syntax unlikely, it makes
it impossible.

The **evolving pool** is real too, and it carries a warning from our own
measurements that I would not have believed if it had come from anywhere else:
the same procedure, the same text, the same rule, classified as *interface
compensation* on a 4B model and as *persistent gain* on a 12B. Whether an expert
is real is not a property of the expert. Any tournament scored against a single
target will breed adapters that flatter that target, which is how an evolution
loop produces confident nonsense on a schedule.

## What I would have built

Without the check, I would have built tree attention across adapters — the
genuinely hard part, where branches from different adapters cannot share a KV
cache the way one drafter's branches can — in service of a router that selects
for blandness.

The idea was good enough that I would have got quite far before anything told me.
Nothing would have failed. The system would have run, the branches would have
competed, a winner would have been emitted every time, and the winner would have
been the adapter that learned the least. The numbers would have looked fine.

That is the failure mode worth naming, and it is why the first thing in the
repository is the objection rather than the diagram.

---

*The repository is [`speculative-experts`](https://github.com/EvolvingAgentsLabs/speculative-experts).
Nothing is built. The first thing that runs will be the headroom check, and the
second will be the correlation that decides the rest.*

*Thanks to [Ismael Faro](https://github.com/ismaelfaro), who suggested studying
this, and was right for a reason neither of us had in mind at the time.*
