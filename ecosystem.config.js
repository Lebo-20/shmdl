module.exports = {
  apps: [
    {
      name: "shortmax-bot",
      script: "/root/shmdl/venv/bin/python3",
      args: "main.py",
      cwd: "/root/shmdl",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "production",
      }
    }
  ]
};
