import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import { z } from "zod";
import { getDemoScreening, screenUploads } from "./resumeScreeningService";

const uploadSchema = z.object({
  filename: z.string().min(1).max(180),
  mimeType: z.string().max(120),
  contentBase64: z.string().min(1),
});

export const appRouter = router({
    // if you need to use socket.io, read and register route in server/_core/index.ts, all api should start with '/api/' so that the gateway can route correctly
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),

  screening: router({
    demo: publicProcedure.query(() => getDemoScreening()),
    analyze: publicProcedure.input(z.object({
      jobDescription: uploadSchema,
      resumes: z.array(uploadSchema).min(10).max(30),
    })).mutation(({ input }) => screenUploads(input.jobDescription, input.resumes)),
  }),

  // TODO: add feature routers here, e.g.
  // todo: router({
  //   list: protectedProcedure.query(({ ctx }) =>
  //     db.getUserTodos(ctx.user.id)
  //   ),
  // }),
});

export type AppRouter = typeof appRouter;
