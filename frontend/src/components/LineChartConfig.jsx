const chartConfig = {
  type: "line",
  data: {
    labels: [],
    datasets: [
      {
        data: [],
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    legend: {
      display: false,
    },
    scales: {
      xAxes: [
        {
          display: true,
          type: "time",
          time: {
            parser: "DD-MM-YYThh:mm:ss",
            displayFormats: {
              hour: "DD-MM-YYThh:mm:ss",
              minute: "DD-MM-YYThh:mm:ss",
              second: "DD-MM-YYThh:mm:ss",
              hour: "DD-MM-YYThh:mm",
              day: "DD-MM-YYYY",
              week: "DD-MM-YYYY",
              month: "MM-YYYY",
              year: "MM-YYYY",
            },
          },
        },
      ],
    },
  },
};

const dataConfig = {
  fill: false,
  pointRadius: 1,
  pointHoverRadius: 20,
  borderWidth: 3,
};

const chartColors = {
  cyan: "#00ffff",
  darkgrey: "#a9a9a9",
  darksalmon: "#e9967a",
  gold: "#ffd700",
  green: "#008000",
  lime: "#00ff00",
  magenta: "#ff00ff",
  maroon: "#800000",
  orange: "#ffa500",
  pink: "#ffc0cb",
};

export { chartConfig, dataConfig, chartColors };
