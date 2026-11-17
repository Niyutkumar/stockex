# StockEx front end

React + Vite. Talks to the FastAPI backend in the folder above.

## Run it

    npm install
    npm run dev

Then open http://localhost:5173

The backend must be running too, in a separate terminal from the project
root:

    source .venv/bin/activate
    uvicorn app.main:app --reload

## How the two connect

`vite.config.js` proxies anything starting with `/api` to
`http://127.0.0.1:8000`. The browser therefore only ever sees one origin
during development, so CORS never comes into it and no API URL is
hard-coded anywhere in the source.

## Layout

    src/
      api/client.js        every call to the backend, in one file
      context/             who is signed in; light or dark
      components/          logo, layout rail, the two charts
      pages/               one file per screen
      theme.css            colour tokens for both themes
      app.css              component styles, written against the tokens
      utils/format.js      Indian number and date formatting

## Themes

`theme.css` defines the full light palette on `:root`, then redefines
only the tokens for dark — once under `prefers-color-scheme` for the
operating system setting, once under `[data-theme="dark"]` for the
toggle, so an explicit choice wins either way.

The two palettes are not inversions of one another. The gain green is
`#047857` in light and `#3ddc84` in dark, because a mint green on white
measures about 2:1 against the background and is unreadable; the chart
gradient is also nearly twice as strong in dark mode to stay visible.
