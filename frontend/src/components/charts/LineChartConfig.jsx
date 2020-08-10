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
            parser: "DD-MM-YY HH:mm:ss",
            // unitStepSize: 1,
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
