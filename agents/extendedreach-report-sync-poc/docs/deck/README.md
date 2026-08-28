# Executive proposal deck

`build_proposal_deck.js` generates `../ExtendedReach-Automation-Proposal.pptx`
— nine slides for presenting this project to the leadership team as a
decision, not a demo.

```bash
npm install pptxgenjs      # once
node build_proposal_deck.js
```

The deck is generated rather than hand-built so the figures and the status
claims can be updated in one place when they change. Two things in it will go
stale and matter:

- **Slide 3** carries real figures from the audit (1,556 overdue, 394 awaiting
  approval, 41% on time). Re-check them against the current export before
  presenting.
- **Slide 6** says the tool has never been run against the live portal. The
  moment that stops being true, change it. Presenting an out-of-date status
  claim is the fastest way to lose the room.

Speaker notes are on every slide and carry the argument, not a script.
