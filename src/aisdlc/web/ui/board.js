// The board, drawn from what the API says and never from anything computed here.
//
// **The columns come from the API.** A board that assembled its own columns in JavaScript would
// have two places where a `Stage` becomes a column, and the two would agree until somebody added
// a stage in one of them. Same for every fact on a card: this file renders and it does not decide.
//
// **Two facts are computed here and both are about the reader, not the domain:** the elapsed time
// on a card, and whether the gate buttons are enabled. The second is a safety property copied from
// the Qt console this was ported from — a decision is not offered until there is a name *and* a
// reason, because a decision with no grounds is a coin flip written down at the one place a coin
// flip is worst.

const theBoard = document.getElementById("the-board");
const theStory = document.getElementById("the-story");
const theStoryBody = document.getElementById("the-story-body");
const nothingHere = document.getElementById("nothing-here");
const theForm = document.getElementById("ask-for-something");
const theStartButton = document.getElementById("start-a-run");
const whatHappenedToTheRequest = document.getElementById("what-happened-to-the-request");

let whichRunIsOpen = null;
let theStreamOfTheOpenRun = null;

// **One form, and it is the only way a run is started from a browser.** A run's card exists from
// the moment the request is accepted, so this returns as soon as there is a card to show — not
// when the run has done anything. A request that held the browser open for the four minutes a
// clone and a discovery report take would look identical to a server that had dropped it.
theForm.addEventListener("submit", async (whatWasPressed) => {
  whatWasPressed.preventDefault();
  theStartButton.disabled = true;
  whatHappenedToTheRequest.textContent = "starting…";
  whatHappenedToTheRequest.className = "what-happened is-working";

  const answer = await fetch("/api/runs", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      repository_owner: document.getElementById("repository-owner").value.trim(),
      repository_name: document.getElementById("repository-name").value.trim(),
      asked_for: document.getElementById("asked-for").value.trim(),
    }),
  });

  theStartButton.disabled = false;
  if (!answer.ok) {
    // **The server's own sentence, not a status code.** A refusal here is one of three things
    // this system names — a blank field, a model this deployment has not configured, a run id
    // already in use — and each of them says what to do about it.
    const why = await answer.json().catch(() => ({ detail: "the server did not say why" }));
    whatHappenedToTheRequest.textContent = why.detail || "the run did not start";
    whatHappenedToTheRequest.className = "what-happened is-refused";
    return;
  }

  const started = await answer.json();
  whatHappenedToTheRequest.textContent = `${started.work_item_id} is on the board`;
  whatHappenedToTheRequest.className = "what-happened is-working";
  document.getElementById("asked-for").value = "";
  refresh();
});

async function readTheBoard() {
  const answer = await fetch("/api/board");
  return answer.json();
}

function drawTheBoard(theBoard_) {
  const isEmpty = theBoard_.cards.length === 0;
  theBoard.hidden = isEmpty;
  nothingHere.hidden = !isEmpty;
  if (isEmpty) return;

  theBoard.replaceChildren();
  for (const aColumnName of theBoard_.columns) {
    theBoard.appendChild(aColumnIn(aColumnName, theBoard_.cards));
  }
}

function aColumnIn(aColumnName, theCards) {
  const theColumn = document.createElement("section");
  theColumn.className = "a-column";

  const theHeading = document.createElement("h2");
  const inThisColumn = theCards.filter((aCard) => aCard.column === aColumnName);
  theHeading.append(`${aColumnName} `);
  const howMany = document.createElement("span");
  howMany.className = "how-many";
  howMany.textContent = inThisColumn.length;
  theHeading.append(howMany);
  theColumn.append(theHeading);

  for (const aCard of inThisColumn) {
    theColumn.appendChild(aCardIn(aCard));
  }
  return theColumn;
}

function aCardIn(aCard) {
  const theButton = document.createElement("button");
  theButton.className = "a-card";
  theButton.dataset.workItemId = aCard.work_item_id;
  if (aCard.work_item_id === whichRunIsOpen) theButton.classList.add("is-open");
  theButton.addEventListener("click", () => openTheStoryOf(aCard.work_item_id));

  const theTitle = document.createElement("p");
  theTitle.className = "the-title";
  theTitle.textContent = aCard.title;
  theButton.append(theTitle);

  const whereItCameFrom = document.createElement("p");
  whereItCameFrom.className = "where-it-came-from";
  whereItCameFrom.append(whereItCameFromWorth(aCard));
  const thePill = document.createElement("span");
  thePill.className = `a-pill is-${aCard.stage === "DONE" ? "done" : thePillItWears(aCard)}`;
  thePill.textContent = thePillItWears(aCard);
  whereItCameFrom.append(thePill);
  theButton.append(whereItCameFrom);

  const theMeter = document.createElement("p");
  theMeter.className = "the-meter";
  theMeter.textContent = aCard.context.in_words;
  theButton.append(theMeter);

  if (aCard.why_it_was_refused) {
    const why = document.createElement("p");
    why.className = "why-it-was-refused";
    why.textContent = `${aCard.who_refused_it}: ${aCard.why_it_was_refused}`;
    theButton.append(why);
  }

  return theButton;
}

function thePillItWears(aCard) {
  if (aCard.why_it_was_refused) return "refused";
  if (aCard.artifact_it_is_waiting_about) return "waiting";
  if (aCard.stage === "DONE") return "done";
  if (aCard.stage === "IN_PROGRESS_BY_AGENT") return "working";
  return "queued";
}

function whereItCameFromWorth(aCard) {
  const theIdentifier = document.createElement("code");
  theIdentifier.className = "an-identifier";
  theIdentifier.textContent = aCard.work_item_id;
  const where = document.createElement("span");
  where.textContent = `${theIdentifier.textContent} · ${aCard.discipline_in_words ?? aCard.discipline}`;
  return where;
}

async function openTheStoryOf(workItemId) {
  whichRunIsOpen = workItemId;
  theStory.hidden = false;
  const answer = await fetch(`/api/runs/${workItemId}`);
  if (!answer.ok) return;
  drawTheStoryOf(await answer.json());
  listenToWhatThatRunSays(workItemId);
}

function drawTheStoryOf(aRun) {
  // **The guard is armed here, by the draw, and not by the poll.** Arming it in the poll means
  // the first poll after opening sees "nothing has changed", redraws the whole story, and can
  // land between a person's two keystrokes — which is what a browser test caught: fill the name,
  // fill the reason, and the second one landed in a field the first fill had just been removed
  // from. The draw is the thing that knows what is on screen.
  whatTheStoryLastDrew = whatWouldBeDifferentAbout(aRun);
  theStoryBody.replaceChildren();

  const theTitle = document.createElement("h2");
  theTitle.textContent = aRun.card.title;
  theStoryBody.append(theTitle);

  const whereItCameFrom = document.createElement("p");
  whereItCameFrom.className = "where-it-came-from";
  whereItCameFrom.append(whereItCameFromWorth(aRun.card));
  theStoryBody.append(whereItCameFrom);

  if (aRun.card.asked_about) {
    const theFiling = document.createElement("p");
    theFiling.className = "where-it-came-from";
    const aLink = document.createElement("a");
    aLink.href = aRun.card.asked_about;
    aLink.textContent = aRun.card.asked_about;
    theFiling.append(aLink);
    theStoryBody.append(theFiling);
  }

  const whereItIs = howThisRunIsDoing(aRun);
  if (whereItIs) theStoryBody.append(whereItIs);

  theStoryBody.append(theGateToAnswerIn(aRun));
  theStoryBody.append(theChainOfGatesIn(aRun));

  if (aRun.notes.length) {
    theStoryBody.append(aHeading("what the agents concluded"));
    for (const aNote of aRun.notes) {
      const aNoteIn = document.createElement("p");
      aNoteIn.className = "a-note";
      const who = document.createElement("span");
      who.className = "who";
      who.textContent = aNote.said_by;
      aNoteIn.append(who, "\n", aNote.what_was_said);
      theStoryBody.append(aNoteIn);
    }
  }

  theStoryBody.append(aHeading("what this run has said"));
  const theSaid = document.createElement("ul");
  theSaid.className = "a-said";
  for (const anEvent of aRun.what_it_said) {
    theSaid.append(whatARunSaidIn(anEvent));
  }
  theStoryBody.append(theSaid);
}

// **The two things only the process knows, and a card cannot hold either.** A work item at
// AWAITING_HUMAN_APPROVAL is the same stage whether the run is parked at its gate waiting for a
// person, reading a repository, or dead on the floor with an exception nobody was watching for.
// The stage is on disk and the run is in memory, so this is the one place the two are joined —
// and a board that left it out would show a stopped run as one that is still thinking.
function howThisRunIsDoing(aRun) {
  if (aRun.how_it_ended) {
    return aLine("is-stuck", `this run stopped: ${aRun.how_it_ended}`);
  }
  if (aRun.is_still_working) {
    return aLine("is-working", "working — an agent has it");
  }
  if (aRun.the_question) {
    return aLine("is-waiting", "waiting for you");
  }
  return null;
}

function aLine(whatClass, whatItSays) {
  const theLine = document.createElement("p");
  theLine.className = `where-it-is ${whatClass}`;
  theLine.textContent = whatItSays;
  return theLine;
}

function aHeading(whatItSays) {
  const theHeading = document.createElement("h3");
  theHeading.className = "a-heading";  theHeading.textContent = whatItSays;
  return theHeading;
}

function whatARunSaidIn(anEvent) {
  const aLine = document.createElement("li");
  const when = document.createElement("span");
  when.className = "when";
  when.textContent = new Date(anEvent.happened_at).toLocaleTimeString();
  const what = document.createElement("span");
  what.textContent = anEvent.what_happened;
  aLine.append(when, what);
  return aLine;
}

function theChainOfGatesIn(aRun) {
  const theChain = document.createElement("ul");
  theChain.className = "the-gates";

  for (const aGate of aRun.gates) {
    const aLine = document.createElement("li");
    const whichArtifact = document.createElement("span");
    whichArtifact.textContent = `${aGate.artifact_id} v${aGate.artifact_version}`;
    // **The verdict is read from the decision and not assumed.** `gates` is every answer this run
    // collected, refusals included — a refusal leaves a decision and no approval, which is the
    // whole reason the two are separate tables. A chain that called all of them "approved" drew
    // the one decision a person is most certain about in the colour of the opposite.
    const theVerdict = document.createElement("span");
    theVerdict.className = aGate.approved ? "verdict was-approved" : "verdict was-refused";
    theVerdict.textContent = aGate.approved ? "approved" : "refused";
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = aGate.decided_by;
    const theReason = document.createElement("span");
    theReason.className = "the-reason";
    theReason.textContent = aGate.reason;
    aLine.append(whichArtifact, theVerdict, who, theReason);
    theChain.append(aLine);
  }

  if (aRun.the_question) {
    const aLine = document.createElement("li");
    const whichArtifact = document.createElement("span");
    whichArtifact.textContent = `${aRun.the_question.artifact_id} v${aRun.the_question.artifact_version}`;
    const theVerdict = document.createElement("span");
    theVerdict.className = "verdict is-awaiting";
    theVerdict.textContent = "awaiting you";
    aLine.append(whichArtifact, theVerdict);
    theChain.append(aLine);
  }

  theChain.append(aLineForEachGateNeverReached(aRun));
  return theChain;
}

function aLineForEachGateNeverReached(aRun) {
  const aLine = document.createElement("li");
  const notYet = document.createElement("span");
  notYet.className = "verdict not-yet";
  notYet.textContent = "not yet";
  const whichArtifact = document.createElement("span");
  whichArtifact.textContent =
    aRun.card.asked_about ? "the delivery" : "the rest of the pipeline";
  aLine.append(whichArtifact, notYet);
  return aLine;
}

function theGateToAnswerIn(aRun) {
  if (!aRun.the_question) return document.createElement("div");

  const thePanel = document.createElement("div");
  thePanel.className = "the-gate-to-answer";

  const theHeading = document.createElement("h3");
  theHeading.textContent = `${aRun.the_question.artifact_id} v${aRun.the_question.artifact_version}`;
  thePanel.append(theHeading);

  const whatItIs = document.createElement("p");
  whatItIs.textContent = "This run is waiting for you. Read the artifact, then say who you are and why.";
  thePanel.append(whatItIs);

  const theNameField = anInputIn("Your name — this is recorded as the decision", "name");
  const theReasonField = anInputIn("Why", "reason", true);
  thePanel.append(theNameField, theReasonField);
  const theName = theNameField.querySelector("input");
  const theReason = theReasonField.querySelector("input");

  const theButtons = document.createElement("div");
  theButtons.className = "answer-the-gate";
  const approve = aButtonIn("approve", "Approve");
  const refuse = aButtonIn("refuse", "Refuse");
  theButtons.append(approve, refuse);
  thePanel.append(theButtons);

  const whyItIsOff = document.createElement("p");
  whyItIsOff.className = "why-the-button-is-off";
  whyItIsOff.textContent = "Both a name and a reason are needed. A decision with no grounds is a coin flip written down.";
  thePanel.append(whyItIsOff);

  const buttonsFollowWhatWasTyped = () => {
    const isReady = theName.value.trim() !== "" && theReason.value.trim() !== "";
    approve.disabled = !isReady;
    refuse.disabled = !isReady;
    whyItIsOff.hidden = isReady;
  };
  theName.addEventListener("input", buttonsFollowWhatWasTyped);
  theReason.addEventListener("input", buttonsFollowWhatWasTyped);
  buttonsFollowWhatWasTyped();

  approve.addEventListener("click", () => answerThisGate(aRun, true));
  refuse.addEventListener("click", () => answerThisGate(aRun, false));

  return thePanel;
}

function anInputIn(whatItIs, theName, isLonger = false) {
  // Returns the *field*, not the input and not the label, and that is deliberate: the first
  // version returned the label, so every caller that asked it for `.value` read `undefined`
  // and the gate panel's buttons stayed disabled with nothing on screen to say why. A caller
  // gets the thing it puts on the page and asks the page for the input.
  const theField = document.createElement("div");
  const theLabel = document.createElement("label");
  theLabel.textContent = whatItIs;
  theLabel.htmlFor = theName;
  const theInput = document.createElement("input");
  theInput.id = theName;
  theInput.name = theName;
  if (isLonger) theInput.placeholder = "a sentence a reader could argue with";
  theField.append(theLabel, theInput);
  return theField;
}

function aButtonIn(which, whatItSays) {
  const theButton = document.createElement("button");
  theButton.className = which;
  theButton.textContent = whatItSays;
  theButton.disabled = true;
  return theButton;
}

async function answerThisGate(aRun, approved) {
  const theName = theStoryBody.querySelector('input[name="name"]');
  const theReason = theStoryBody.querySelector('input[name="reason"]');
  const answer = await fetch(`/api/runs/${aRun.card.work_item_id}/decisions`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ approved, decided_by: theName.value, reason: theReason.value }),
  });

  if (!answer.ok) {
    const whatWentWrong = await answer.json();
    window.alert(whatWentWrong.detail ?? "the gate refused that decision");
    return;
  }
  await refresh();
  await openTheStoryOf(aRun.card.work_item_id);
}

function listenToWhatThatRunSays(workItemId) {
  if (theStreamOfTheOpenRun) theStreamOfTheOpenRun.close();
  theStreamOfTheOpenRun = new EventSource(`/api/runs/${workItemId}/events`);
  theStreamOfTheOpenRun.addEventListener("what_it_said", refresh);
  theStreamOfTheOpenRun.addEventListener("what_it_is_asking", refresh);
}

async function refresh() {
  drawTheBoard(await readTheBoard());
  if (!whichRunIsOpen) return;

  const answer = await fetch(`/api/runs/${whichRunIsOpen}`);
  if (!answer.ok) return;
  const theRun = await answer.json();

  // **The story is redrawn only when something a reader can see has changed.** The board polls
  // every two seconds, and a redraw replaces every node under the panel — so a person who had
  // typed their name and half a reason had it deleted twice a second and no test in the project
  // could have seen it, because nothing in the API was wrong. What is compared is the question
  // being asked and the stage the run is at: the two things that change the panel's shape.
  if (whatWouldBeDifferentAbout(theRun) === whatTheStoryLastDrew) return;
  drawTheStoryOf(theRun);
}

let whatTheStoryLastDrew = "";

function whatWouldBeDifferentAbout(aRun) {
  return JSON.stringify([
    aRun.the_question,
    aRun.card.stage,
    aRun.gates.length,
    aRun.what_it_said.length,
    aRun.is_still_working,
    aRun.how_it_ended,
  ]);
}

document.getElementById("close-the-story").addEventListener("click", () => {
  theStory.hidden = true;
  whichRunIsOpen = null;
  if (theStreamOfTheOpenRun) theStreamOfTheOpenRun.close();
  theStreamOfTheOpenRun = null;
});

refresh();
setInterval(refresh, 2000);
