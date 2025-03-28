const webpack = require("webpack");

module.exports = {
  webpack: {
    configure: {
      resolve: {
        fallback: {
          crypto: require.resolve("crypto-browserify"),
          os: require.resolve("os-browserify/browser"),
          https: require.resolve("https-browserify"),
          http: require.resolve("stream-http"),
          stream: require.resolve("stream-browserify"),
          buffer: require.resolve("buffer/"),
        },
      },
    },
    plugins: [
      new webpack.ProvidePlugin({
        Buffer: ["buffer", "Buffer"],
        process: "process/browser",
      }),
    ],
  },
  style: {
    postcss: {
      mode: "file",
    },
  },
};
