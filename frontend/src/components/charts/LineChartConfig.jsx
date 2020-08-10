const lineChartConfig = {
  type: "line",
  data: {
    labels: [],
    datasets: [
      {
        data: [],
        label: "Petition ID: 99999",
        backgroundColor: ["rgba(255, 99, 132, 0.2)"],
        borderColor: ["rgba(255, 99, 132, 1)"],
        borderWidth: 1,
      },
    ],
  },
  options: {
    scales: {
      xAxes: [
        {
          display: true,
          type: "time",
          // time: {
          //   parser: "MM/DD/YYYY HH:mm",
          //   // tooltipFormat: "ll HH:mm",
          //   // unit: "hour",
          //   unitStepSize: 1,
          //   displayFormats: {
          //     day: "MM/DD/YYYY HH:mm",
          //   },
          // },
        },
      ],
    },
  },
};

export default lineChartConfig;

// https://stackoverflow.com/questions/54334676/chart-js-format-date-in-label
// https://stackoverflow.com/questions/53669361/how-to-display-date-as-label-on-x-axis-in-chart-js
