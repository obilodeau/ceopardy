#!/bin/bash

mkdir -p static/vendor
copyfiles -u 1 node_modules/jquery/dist/jquery.min.js static/vendor/
copyfiles -u 1 node_modules/font-awesome/css/font-awesome.min.css static/vendor/
copyfiles -u 1 node_modules/font-awesome/fonts/\* static/vendor/
copyfiles -u 1 node_modules/socket.io-client/dist/socket.io.min.js static/vendor/
