const lineChartConfig = {
  type: "line",
  data: {
    labels: [],
    datasets: [
      {
        data: [],
        label: "",
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
            parser: "DD-MM-YYThh:mm:ss",
            // unitStepSize: 1,
            displayFormats: {
              hour: "DD-MM-YYThh:ss:mm",
              millisecond: "DD-MM-YYThh:ss:mm",
              second: "DD-MM-YYThh:ss:mm",
              minute: "DD-MM-YYThh:ss:mm",
              hour: "DD-MM-YYThh:ss:mm",
              day: "DD-MM-YYThh:ss:mm",
              week: "DD-MM-YYThh:ss:mm",
              month: "DD-MM-YYThh:ss:mm",
              quarter: "DD-MM-YYThh:ss:mm",
              year: "DD-MM-YYThh:ss:mm",
            },
          },
        },
      ],
    },
  },
};

export default lineChartConfig;
