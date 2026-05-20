import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const { question, chat_history } = await req.json();

    const ML_URL = process.env.AZURE_ML_ENDPOINT_URL;
    const ML_KEY = process.env.AZURE_ML_ENDPOINT_KEY;
    const GENAI_URL = process.env.AZURE_FOUNDRY_ENDPOINT_URL;
    const GENAI_KEY = process.env.AZURE_FOUNDRY_ENDPOINT_KEY;

    if (!ML_URL || !ML_KEY || !GENAI_URL || !GENAI_KEY) {
      return NextResponse.json({ error: 'Missing environment variables' }, { status: 500 });
    }

    const startML = Date.now();
    const mlPromise = fetch(ML_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ML_KEY}`,
      },
      body: JSON.stringify({
        data: [{ text: question }],
      }),
    }).then(async res => {
      const duration = (Date.now() - startML) / 1000;
      return { data: res.ok ? await res.json() : null, duration };
    }).catch(() => ({ data: null, duration: 0 }));

    const startGenAI = Date.now();
    const genaiPromise = fetch(GENAI_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${GENAI_KEY}`,
        'x-ms-client-request-id': crypto.randomUUID(),
      },
      body: JSON.stringify({
        question,
        chat_history,
      }),
    }).then(async res => {
      const duration = (Date.now() - startGenAI) / 1000;
      return { 
        ok: res.ok, 
        status: res.status, 
        data: res.ok ? await res.json() : null, 
        error: res.ok ? null : await res.text(),
        duration,
        traceId: res.headers.get('x-ms-client-request-id') || res.headers.get('x-ms-promptflow-run-id') || 'N/A'
      };
    });

    const [mlResult, genaiResult] = await Promise.all([mlPromise, genaiPromise]);

    if (!genaiResult.ok) {
      return NextResponse.json({ error: `GenAI Endpoint Error: ${genaiResult.status} - ${genaiResult.error}` }, { status: genaiResult.status || 500 });
    }

    return NextResponse.json({
      intent: mlResult.data?.predictions?.[0] || 'Unknown',
      ml_duration: mlResult.duration,
      answer: genaiResult.data.answer,
      context: genaiResult.data.context,
      trace_id: genaiResult.traceId,
      genai_duration: genaiResult.duration, 
    });

  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
