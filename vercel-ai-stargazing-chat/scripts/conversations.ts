// Scripted multi-turn conversations the demo plays over HTTP. The last one
// deliberately asks for things the fictional guide does not contain, so the
// online judge has something to catch.
export interface Conversation {
  title: string;
  turns: string[];
}

export const conversations: Conversation[] = [
  {
    title: "Planning a Jupiter night",
    turns: [
      "When is Jupiter at opposition this autumn, and which Circle telescope should I use for the cloud belts?",
      "How long before sunset-dark should I arrive, and what light can I use while I set up?",
    ],
  },
  {
    title: "Borrowing a loaner",
    turns: [
      "I have never used a telescope. Which loaner is better for the Orion Nebula, Pip or Marlow?",
      "How long can I keep it, and do I need to do anything before observing?",
    ],
  },
  {
    title: "Questions the guide cannot answer",
    turns: [
      "Does the Circle lend a solar filter so I can watch sunspots?",
      "What is the price of the Circle's membership, and which camera should I buy for deep-sky astrophotography?",
    ],
  },
];
