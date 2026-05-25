// SPDX-License-Identifier: GPL-3.0-or-later
import { io } from "socket.io-client";

// Single socket on the /game namespace. Host and viewer both listen here
// for realtime broadcasts of state changes.
let socket = null;

export function getSocket() {
  if (!socket) {
    socket = io("/game", {
      autoConnect: false,
      transports: ["websocket", "polling"],
    });
  }
  return socket;
}
