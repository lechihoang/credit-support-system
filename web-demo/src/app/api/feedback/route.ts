import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const { trace_id, useful, question, answer } = await req.json();

    const GENAI_URL = process.env.AZURE_FOUNDRY_ENDPOINT_URL;
    const GENAI_KEY = process.env.AZURE_FOUNDRY_ENDPOINT_KEY;

    if (!GENAI_URL || !GENAI_KEY) {
      return NextResponse.json({ error: 'Missing configuration' }, { status: 500 });
    }

    const feedback_url = GENAI_URL.replace('/score', '/feedback');

    const response = await fetch(feedback_url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${GENAI_KEY}`,
      },
      body: JSON.stringify({
        trace_id,
        payload: {
          useful,
          question,
          answer
        }
      }),
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to send feedback' }, { status: response.status });
    }

    return NextResponse.json({ success: true });

  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
