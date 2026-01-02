import { Resend } from 'resend';
import { WeeklyDigestEmail } from '../emails/weekly-digest';
import * as React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render } from '@react-email/components';

const resend = new Resend(process.env.RESEND_API_KEY);

async function main() {
    if (!process.env.RESEND_API_KEY) {
        console.error("Error: RESEND_API_KEY environment variable is not set.");
        process.exit(1);
    }

    const jsonPath = path.join(process.cwd(), '../tmp/weekly_digest.json');
    console.log(`Reading digest data from: ${jsonPath}`);

    if (!fs.existsSync(jsonPath)) {
        console.error(`Error: Digest file not found at ${jsonPath}`);
        process.exit(1);
    }

    const jsonContent = fs.readFileSync(jsonPath, 'utf-8');
    const digestData = JSON.parse(jsonContent);

    console.log(`Generating email for ${digestData.newArrivals.length} new arrivals...`);

    const emailHtml = await render(<WeeklyDigestEmail digestData={digestData} />);

    try {
        const data = await resend.emails.send({
            from: 'Mubi Digest <noreply@kubi.icu>', // Update this with your verified domain
            to: ['kubi.ui@gmail.com'], // Update recipient or use env var
            subject: `Mubi Weekly Digest - ${digestData.newArrivals.length} New Arrivals`,
            html: emailHtml,
        });

        console.log('Email sent successfully:', data);
    } catch (error) {
        console.error('Error sending email:', error);
        process.exit(1);
    }
}

main();
