const cfg = {
  _id: "rs0",
  members: [
    { _id: 0, host: "mongo1:27017", priority: 2 },
    { _id: 1, host: "mongo2:27017", priority: 1 },
    { _id: 2, host: "mongo3:27017", priority: 1 },
  ],
};

try {
  rs.initiate(cfg);
} catch (e) {
  // If already initialized, force reconfigure to host-reachable addresses.
  rs.reconfig(cfg, { force: true });
}

rs.status();
