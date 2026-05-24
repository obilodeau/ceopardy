# Ceopardy

The Hacker Jeopardy Game Board we use at NorthSec.

## Screenshots

This is what the crowd sees:

![The Viewer Interface Displaying the Game Board](docs/images/viewer-board.png)

When a clue is displayed:

![The Viewer Interface Displaying a Clue](docs/images/viewer-clue.png)

This is the host interface, how you control the game:

![The Host Interface](docs/images/host.png)

Note that there are two drawers that can be opened by clicking on the brown
arrows at the top and at the bottom of the screen. The top drawer contains
the functions to change team names. The bottom drawer provides functions to
display a custom message on the board or to pause a game.


## Architecture

Starting with v0.5, Ceopardy is split in two parts:

- A Python/Flask back-end that exposes a small REST API (`/api/v1/...`) and
  broadcasts state changes over a single Socket.IO namespace (`/game`).
- A Vite + Vue 3 front-end (in `frontend/`) that powers the crowd-facing
  viewer, the host UI, and the start screen.


## First time deployment

You need Python, pip, virtualenv and Node.js (LTS). The tl;dr:

    make venv
    source .venv/bin/activate    # bash/zsh
    source .venv/bin/activate.fish    # fish
    make init                    # seed data/ and game-media/ from templates
    npm install --prefix frontend
    npm run build --prefix frontend
    python run.py

`make venv` creates `.venv/` and installs both runtime and dev requirements.
`make init` is a one-time step that copies starter `data/1st.round` and
`data/Questions.cp` into the repo and creates `game-media/`. Edit those files
to set up your game.

### Optional: direnv

If you use [direnv](https://direnv.net/), the repo ships an `.envrc` that puts
`.venv/bin` on your `PATH` automatically when you `cd` into the directory —
works in bash, zsh, and fish. Install direnv (see
[upstream docs](https://direnv.net/docs/installation.html) for shell hook setup),
then from the repo root:

    make venv        # create the venv first; direnv won't do this for you
    direnv allow     # trust the .envrc

After that, entering the directory activates the venv and leaving deactivates
it — no manual `source` needed.

Then open [the host view](http://127.0.0.1:5000/host) to set up the game.
[The players' view](http://127.0.0.1:5000/) (also known as the viewer) can be
opened at any time.

`python run.py` runs the built-in dev server (debug + reloader). For
production, run it under gunicorn with the eventlet worker. Socket.IO requires
a single worker process unless you also configure a Redis message queue:

    pip install gunicorn
    gunicorn -k eventlet -w 1 -b 127.0.0.1:5000 'run:app'

Put nginx (or similar) in front for TLS and to expose it on the network — the
app itself binds to localhost because the host interface has no auth.


## Development

Run Flask and Vite side by side. Vite hot-reloads the UI and proxies
`/api` and `/socket.io` to Flask.

    # terminal 1 - Flask
    python run.py

    # terminal 2 - Vite dev server
    npm run dev --prefix frontend

Then open http://localhost:5173/.


## Install as a CLI (pipx)

Once published, Ceopardy can be installed as a stand-alone command:

    pipx install ceopardy
    mkdir my-game && cd my-game
    ceopardy init        # scaffolds data/ and game-media/ in CWD
    # edit data/Questions.cp and data/1st.round
    ceopardy             # or `ceopardy serve` — starts the server

`ceopardy init` never overwrites existing files; it's safe to re-run. The
server, the SQLite database, and the question files all resolve relative to
the directory you run `ceopardy` from, so keep one directory per game.


## Prepare a game

Game data goes in `data/`. There you should add round files (create a `.round`
file) and questions in `Questions.cp`. The format is pretty self explanatory.
Run `ceopardy init` (or `make init` from the repo) to get a working starter
set; `data/1st.round` and `data/Questions.cp` are the minimal example.
User-supplied media referenced by questions (e.g. `[img:photo.png]`) goes in
`game-media/` next to `data/`.

> **Note:** In order to avoid dataloss due to a crash, Ceopardy is backed by a
> database where transactions are pushed when the hosts submit the points. This
> has the flipside requiring games to be finalized before a new one can be
> started. Make sure that you always push the "Game over" button before
> reloading to start a new game.
