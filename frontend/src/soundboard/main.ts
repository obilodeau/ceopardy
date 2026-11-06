// SPDX-License-Identifier: GPL-3.0-or-later
// The remote sound operator's page: a Vite entry of its own, so its bundle
// carries none of the host or viewer code.
import { createApp } from "vue";

import SoundboardApp from "./SoundboardApp.vue";

createApp(SoundboardApp).mount("#app");
