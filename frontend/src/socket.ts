// SPDX-License-Identifier: GPL-3.0-or-later
import { io, type Socket } from "socket.io-client";

// Single socket on the /game namespace. Host and viewer both listen here
// for realtime broadcasts of state changes.
let socket: Socket | null = null;

export function getSocket(): Socket {
  if (!socket) {
    socket = io("/game", {
      autoConnect: false,
      transports: ["websocket", "polling"],
    });
  }
  return socket;
}
