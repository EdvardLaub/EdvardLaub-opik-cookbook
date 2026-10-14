import { handleChat } from "../../../lib/chat-handler";

export const maxDuration = 30; // route segment config must be a literal here
export const POST = (req: Request) => handleChat(req);
