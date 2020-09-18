module.exports = {
  style: {
    postcss: {
      plugins: [require("postcss-nested"), require("postcss-responsive-type")()],
    },
  },
};
