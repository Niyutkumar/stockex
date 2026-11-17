# Front end image, two stages.
#
# Stage one builds the static bundle with Node. Stage two serves it with
# nginx and throws Node away — the final image carries no build tools and
# no node_modules, which takes it from roughly 1 GB to about 50 MB.

FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
