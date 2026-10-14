// Everything the guide "knows" about the (fictional) Fernwick Museum of Natural History.
// Plain data + two pure functions, so the offline tests can cover them without a model.

export interface Exhibit {
  name: string;
  hall: string;
  blurb: string;
}

export const MUSEUM_NAME = "Fernwick Museum of Natural History";

export const EXHIBITS: Exhibit[] = [
  { name: "Brontë the Diplodocus", hall: "Great Hall", blurb: "A 21-metre cast skeleton that greets you at the entrance." },
  { name: "Amber Room", hall: "Hall of Ancient Forests", blurb: "Insects, spiders and a tiny frog preserved in 40-million-year-old amber." },
  { name: "Tidepool Touch Tank", hall: "Shoreline Gallery", blurb: "Hands-on tank with starfish and hermit crabs. Open 10:30-15:30 only." },
  { name: "Meteorite Vault", hall: "Cosmos Gallery", blurb: "A 3-tonne iron meteorite you can touch, plus a dimly lit crystal case." },
];

export const HOURS = [
  "Tuesday to Friday: 09:30-17:00",
  "Saturday and Sunday: 09:00-18:00",
  "Monday: closed (except school holidays, 10:00-16:00)",
  "Last entry is 45 minutes before closing.",
];

export const ACCESSIBILITY = [
  "Step-free entrance on Marlow Street; lifts reach every floor.",
  "Free wheelchairs and folding stools at the cloakroom (first come, first served).",
  "Quiet hour every Wednesday 09:30-10:30: lights dimmed, audio exhibits off.",
  "Assistance dogs are welcome everywhere. Audio descriptions are available in the museum app.",
];

export const TICKETS = {
  adult: 14,
  child: 7, // ages 5-15; under 5 free
  senior: 11, // 65+
  family: 38, // 2 adults + up to 3 children
  note: "Tickets for a specific day can be changed free up to 24 hours before. Carers of visitors with a disability enter free.",
};

export function buildSystemPrompt(): string {
  const exhibits = EXHIBITS.map((e) => `- ${e.name} (${e.hall}): ${e.blurb}`).join("\n");
  return [
    `You are the visitor guide for the ${MUSEUM_NAME}. Be warm, brief and concrete (at most 4 sentences).`,
    "Only state facts from the list below. If something is not covered, say you are not sure and",
    "suggest asking at the information desk. Never invent prices, times or exhibits.",
    "",
    "Exhibits:",
    exhibits,
    "",
    "Opening hours:",
    HOURS.map((h) => `- ${h}`).join("\n"),
    "",
    "Accessibility:",
    ACCESSIBILITY.map((a) => `- ${a}`).join("\n"),
    "",
    "Tickets (GBP):",
    `- Adult ${TICKETS.adult}, child ${TICKETS.child}, senior ${TICKETS.senior}, family ${TICKETS.family}.`,
    `- ${TICKETS.note}`,
  ].join("\n");
}

/** Price of a party in GBP. The family ticket is used whenever it is cheaper. */
export function quoteTickets(adults: number, children: number, seniors = 0): number {
  const separate = adults * TICKETS.adult + children * TICKETS.child + seniors * TICKETS.senior;
  const familyFits = adults === 2 && seniors === 0 && children >= 1 && children <= 3;
  return familyFits ? Math.min(separate, TICKETS.family) : separate;
}
