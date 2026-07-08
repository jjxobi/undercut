import "./HowItWorks.css";

interface HowItWorksProps {
  onBack: () => void;
}

function HowItWorks({ onBack }: HowItWorksProps) {
  return (
    <div className="how-it-works">
      <button type="button" className="how-it-works-back" onClick={onBack}>
        &larr; Back to the tool
      </button>

      <article className="how-it-works-body">
        <h2 className="how-it-works-title">How this works</h2>

        <section className="how-it-works-section">
          <h3 className="blade-label">The problem</h3>
          <p>
            In Formula 1, a pit stop for fresh tyres costs around 20-25 seconds. But if a safety car happens to be
            out at the exact moment you pit, that cost drops by roughly 70% -- because the whole field is driving
            slowly anyway, so you lose almost nothing by comparison.
          </p>
          <p>
            That's the whole problem in one sentence:{" "}
            <strong>the best time to change your tyres depends on something you can't know in advance.</strong> A
            team has to commit to a plan -- which tyres, and roughly when to change them -- before the race even
            starts, with no idea whether a safety car is coming, or when.
          </p>
          <p>
            Most of the time, teams plan as if it won't happen. This project asks: how much does that confidence
            actually cost, on average, and can a smarter plan do better without needing to predict the future?
          </p>
        </section>

        <section className="how-it-works-section">
          <h3 className="blade-label">How it decides</h3>
          <p>
            Three things had to be learned from real data before any decision could be made, and then one more step
            actually makes the call.
          </p>
          <ol className="how-it-works-steps">
            <li>
              <strong>How fast do tyres wear out?</strong>
              <p>
                Using real lap times from hundreds of past races, the tool learns -- for each tyre type, at each
                track, in each era of car rules -- how many seconds you lose per lap as the tyres age. This is the
                foundation: it means the tool can predict "20 laps on this tyre will cost you about this many
                seconds," accurately, for almost any circuit.
              </p>
            </li>
            <li>
              <strong>How likely is a safety car, and when?</strong>
              <p>
                Same idea, different question. Using years of real incident history, the tool learns how likely a
                safety car is on each specific lap of each track -- early-race incidents are far more common than
                late-race ones at some circuits, for example. This turns "a safety car might happen" into an actual
                probability, lap by lap.
              </p>
            </li>
            <li>
              <strong>How much does a pit stop really cost, here?</strong>
              <p>A real, track-specific number, pulled from actual pit-lane timing data -- not a guess.</p>
            </li>
            <li>
              <strong>Putting it together.</strong>
              <p>
                With all three pieces of real data in hand, the tool doesn't try to predict the one true outcome of
                the race. Instead, it simulates around 200 different plausible versions of it -- each one a different
                guess at whether and when a safety car shows up, drawn from the real probabilities in step 2. Then
                it checks every reasonable tyre strategy against all 200 simulated races at once, and picks
                whichever plan comes out cheapest <em>on average</em>.
              </p>
            </li>
          </ol>
          <p>
            That's the actual decision rule: not the best plan if everything goes smoothly, and not the safest plan
            if everything goes wrong -- the plan that wins on average across a realistic spread of what could
            actually happen.
          </p>
        </section>

        <section className="how-it-works-section">
          <h3 className="blade-label">What it found</h3>
          <p>
            The real test: does hedging against uncertainty like this actually help, or is it just a more
            complicated way of getting the same answer?
          </p>
          <p>
            Using 652 real past races, this project compared three things for each one: what the driver actually
            did, what this tool's strategy would have recommended beforehand, and what a strategy would have looked
            like with perfect hindsight -- knowing exactly when the safety car was going to come out, if it did at
            all.
          </p>
          <p>
            The result: perfect hindsight was worth about{" "}
            <strong className="how-it-works-delta">17 seconds</strong> a race, on average, over what actually
            happened. This tool's strategy -- recommended <em>without</em> knowing the future, the same way a real
            team has to work -- captured about <strong className="how-it-works-signal">63%</strong> of that value.
          </p>
          <p>
            In plain terms: hedging against uncertainty, instead of just planning for the smoothest possible race,
            recovers most of the advantage that perfect information would have given you. Not all of it -- nobody
            can out-guess a genuinely random event -- but most of it.
          </p>
        </section>

        <section className="how-it-works-section">
          <h3 className="blade-label">What this doesn't claim</h3>
          <p>
            A few things worth being upfront about, since overclaiming would defeat the point of measuring this
            honestly in the first place:
          </p>
          <ul className="how-it-works-list">
            <li>
              This only accounts for tyre wear and pit-stop time. It doesn't account for how a strategy affects your
              position relative to other cars on track -- passing and being passed is a separate, harder problem
              this project measures but doesn't fold into the headline number.
            </li>
            <li>
              A couple of real-world numbers (like exactly how much cheaper a pit stop is under a safety car) are
              reasonable, stated assumptions rather than numbers pulled directly from data.
            </li>
            <li>
              The comparison only includes races where the driver's real strategy was one the tool could have
              proposed itself, so a few unusual real-world strategies (extra precautionary stops, wet-weather races)
              are left out rather than approximated.
            </li>
          </ul>
        </section>

        <section className="how-it-works-section">
          <h3 className="blade-label">Why this exists</h3>
          <p>
            This started as a genuine question -- pit strategy always looked like exactly the kind of decision that's
            hard for a person to reason about but well suited to being modelled properly: real uncertainty, real
            historical data, and a clear way to check afterward whether the smarter approach actually worked.
            Building it end to end -- the statistics, the decision-making under uncertainty, and then honestly
            grading the result against what really happened -- was the point as much as the F1 angle was.
          </p>
        </section>
      </article>
    </div>
  );
}

export default HowItWorks;
