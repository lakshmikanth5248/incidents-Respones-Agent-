import express from 'express';
import path from 'path';
import dotenv from 'dotenv';
import { apiRouter } from './server/routes';

dotenv.config();

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

// Security and body parsers
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logging in dev
app.use((req, res, next) => {
  if (req.url.startsWith('/api')) {
    console.log(`[API ${req.method}] ${req.url}`);
  }
  next();
});

// Mount Backend API routes
app.use('/api', apiRouter);

// Start server with Vite middleware in development or static dist in production
async function startServer() {
  const isProduction = process.env.NODE_ENV === 'production';

  if (!isProduction) {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
    console.log('[Vite] Mounted Vite dev middleware for development');
  } else {
    const distPath = path.resolve(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
    console.log('[Static] Serving built production assets from dist');
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`==================================================`);
    console.log(`AEGIS COMMAND — Full-Stack Server Running`);
    console.log(`URL: http://localhost:${PORT}`);
    console.log(`API Base: http://localhost:${PORT}/api`);
    console.log(`==================================================`);
  });
}

startServer().catch((err) => {
  console.error('[Fatal] Server failed to start:', err);
  process.exit(1);
});
