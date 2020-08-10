const lineChartConfig = {
  type: "line",
  data: {
    labels: [],
    datasets: [
      {
        data: [],
        label: "Petition",
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
          time: {
            parser: "DD-MM-YY HH:mm:ss", //<- use 'parser'
            unit: "hour",
            unitStepSize: 1,
            displayFormats: {
              hour: "DD-MM-YY HH:ss:mm",
            },
          },
        },
      ],
    },
  },
};

export default lineChartConfig;

// https://stackoverflow.com/questions/54334676/chart-js-format-date-in-label
// https://stackoverflow.com/questions/53669361/how-to-display-date-as-label-on-x-axis-in-chart-js
