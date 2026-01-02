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

    // note: We removed the 'render' call from above as we pass the component specificly to the broadcast
    // However, if the user wants to use the 'react' property, we can pass the JSX element directly.
    // But earlier I had `const emailHtml = await render(...)`. I should remove that line if I use the react prop, 
    // OR keep it if I use `html` prop. The user example uses `react: NewsletterEmail(...)`.
    // I will try to use `react` prop.

    try {
        console.log("Creating broadcast draft...");

        // Step 1: Create the Broadcast (Draft)
        const createResponse = await resend.broadcasts.create({
            from: 'Mubi Digest <noreply@kubi.icu>',
            subject: `Mubi Weekly Digest - ${digestData.newArrivals.length} New Arrivals`,
            audienceId: '4fa9b31c-e20d-4d15-a511-a3c11946c5fb', // Using the provided ID
            react: <WeeklyDigestEmail digestData={digestData} />,
        }) as any;

        if (createResponse.error) {
            console.error("Error creating broadcast:", createResponse.error);
            process.exit(1);
        }

        const broadcastId = createResponse.data?.id || createResponse.id;
        console.log(`Broadcast draft created. ID: ${broadcastId}`);

        // Step 2: Trigger the Send
        console.log("Sending broadcast...");
        const sendResponse = await resend.broadcasts.send(broadcastId) as any;

        if (sendResponse.error) {
            console.error("Error sending broadcast:", sendResponse.error);
            process.exit(1);
        }

        console.log('Broadcast sent successfully:', sendResponse.data || sendResponse);

    } catch (error) {
        console.error('Error in email sending process:', error);
        process.exit(1);
    }
}

main();
