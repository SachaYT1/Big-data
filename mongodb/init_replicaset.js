const cfg = {
  _id: "rs0",
  members: [
    { _id: 0, host: "localhost:27020" },
    { _id: 1, host: "localhost:27021" },
    { _id: 2, host: "localhost:27022" },
  ],
};

try {
  rs.initiate(cfg);
} catch (e) {
  // If already initialized, force reconfigure to host-reachable addresses.
  rs.reconfig(cfg, { force: true });
}

rs.status();
