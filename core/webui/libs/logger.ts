import Pino from "pino";

const logger = Pino({
    name: 'JuniorIT',
    level: process.env.NEXT_LOG_LEVEL??'debug',
    transport: {
        target: 'pino-pretty',
        options: {
          translateTime: "SYS:yyyy-mm-dd HH:MM:ss.l",
          colorize: true,
          ignore: 'pid,hostname'
        }
      },
  });

export default logger;