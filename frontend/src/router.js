import { createRouter, createWebHistory } from "vue-router";

import ViewerView from "@/views/ViewerView.vue";
import HostView from "@/views/HostView.vue";
import StartView from "@/views/StartView.vue";
import { useGameStore } from "@/stores/game";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "viewer", component: ViewerView },
    { path: "/viewer", redirect: "/" },
    { path: "/host", name: "host", component: HostView },
    { path: "/start", name: "start", component: StartView },
    // catch-all -> viewer
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

// Redirect to /start when visiting /host while the game has not been setup yet.
router.beforeEach(async (to) => {
  if (to.name !== "host") return true;
  const game = useGameStore();
  if (!game.initialized) {
    await game.refresh();
  }
  if (!game.isInProgress) {
    return { name: "start" };
  }
  return true;
});

export default router;
