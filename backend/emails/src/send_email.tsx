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
        // 1. Get the Audience ID
        const audiences = await resend.audiences.list();
        if (!audiences.data || audiences.data.length === 0) {
            console.error("Error: No audiences found in Resend.");
            process.exit(1);
        }
        const audienceId = audiences.data[0].id;
        console.log(`Using Audience: ${audiences.data[0].name} (${audienceId})`);

        // 2. Get Contacts
        const contacts = await resend.contacts.list({ audience_id: audienceId });
        if (!contacts.data || contacts.data.length === 0) {
            console.error("Error: No contacts found in audience.");
            process.exit(1);
        }

        const activeContacts = contacts.data.filter(c => !c.unsubscribed);
        if (activeContacts.length === 0) {
            console.log("No active (subscribed) contacts found.");
            process.exit(0);
        }

        console.log(`Found ${activeContacts.length} active contacts.`);

        // 3. Batch Send (max 100 per batch)
        const BATCH_SIZE = 100;
        const batches = [];
        for (let i = 0; i < activeContacts.length; i += BATCH_SIZE) {
            batches.push(activeContacts.slice(i, i + BATCH_SIZE));
        }

        for (const batch of batches) {
            // Construct batch payload
            const emailbatch = batch.map(contact => ({
                from: 'Mubi Digest <noreply@kubi.icu>',
                to: [contact.email],
                subject: `Mubi Weekly Digest - ${digestData.newArrivals.length} New Arrivals`,
                html: emailHtml,
            }));

            const { data, error } = await resend.batch.send(emailbatch);

            if (error) {
                console.error('Error sending batch:', error);
                // Continue to next batch? Or exit?
                // process.exit(1);
            } else {
                console.log(`Batch sent successfully: ${data?.data?.length} emails.`);
            }
        }

    } catch (error) {
        console.error('Error in email sending process:', error);
        process.exit(1);
    }
}

main();
