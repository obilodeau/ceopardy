// SPDX-License-Identifier: GPL-3.0-or-later
// The players' buzzer page: a Vite entry of its own, so its bundle carries
// none of the host or viewer code.
import { createApp } from "vue";

import BuzzerApp from "./BuzzerApp.vue";

createApp(BuzzerApp).mount("#app");
