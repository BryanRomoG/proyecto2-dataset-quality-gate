import { Router } from 'express';
import { cocoExportRouter } from '../export/coco.router';
import { annotationsRouter } from './annotations';
import { categoriesRouter } from './categories';
import { contractsRouter } from './contracts';
import { dashboardRouter } from './dashboard';
import { imagesRouter } from './images';
import { pipelineRouter } from './pipeline';

export const apiRouter = Router();

apiRouter.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

apiRouter.use('/annotations', annotationsRouter);
apiRouter.use('/categories', categoriesRouter);
apiRouter.use('/export', cocoExportRouter);
apiRouter.use('/images', imagesRouter);
apiRouter.use('/dashboard', dashboardRouter);
apiRouter.use('/contracts', contractsRouter);
apiRouter.use('/pipeline', pipelineRouter);

// El resto de routers de features (dashboard, ...) se montan aquí de la
// misma forma.
