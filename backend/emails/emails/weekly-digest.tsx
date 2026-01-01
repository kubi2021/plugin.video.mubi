import {
    Body,
    Container,
    Head,
    Heading,
    Hr,
    Html,
    Img,
    Link,
    Preview,
    Section,
    Text,
    Button,
    Tailwind,
} from "@react-email/components";
import * as React from "react";
import * as fs from "fs";
import * as path from "path";

// Load actual data from generated JSON file
const loadDigestData = (): DigestData => {
    const jsonPath = "/Users/kubi/Documents/GitHub/plugin.video.mubi/tmp/weekly_digest.json";
    console.log("Loading JSON from:", jsonPath);

    try {
        const jsonContent = fs.readFileSync(jsonPath, "utf-8");
        const data = JSON.parse(jsonContent);
        console.log("Loaded movies count:", data.newArrivals?.length);
        return data;
    } catch (error) {
        console.error("Error loading JSON:", error);
        // Fallback to sample data if JSON not found
        return {
            generatedAt: "January 01, 2026",
            totalMovies: 2057,
            newArrivals: [
                {
                    title: "Senna (FALLBACK)",
                    year: 2010,
                    bayesian: 8.4,
                    mubi: 8.7,
                    imdb: 8.5,
                    tmdb: 8.1,
                    genres: ["Documentary", "Biography", "Sport"],
                    duration: 106,
                    countries: ["United Kingdom", "France"],
                    directors: ["Asif Kapadia"],
                    synopsis: "A Brazilian motor-racing legend, considered by many the greatest driver to ever live.",
                    imageUrl: "https://assets.mubicdn.net/images/film/37136/image-w448.jpg",
                    trailerUrl: "https://trailers.mubicdn.net/37136/optimised/720p-t-senna.mp4",
                },
            ],
        };
    }
};

const digestData = loadDigestData();
console.log("digestData.newArrivals.length =", digestData.newArrivals.length);

const formatVoters = (count: number) => {
    return new Intl.NumberFormat('en-US', {
        notation: "compact",
        compactDisplay: "short",
        maximumFractionDigits: 1
    }).format(count).toLowerCase();
};

const formatDateRange = (dateString: string) => {
    const endDate = new Date(dateString);
    const startDate = new Date(endDate);
    startDate.setDate(startDate.getDate() - 7);

    const options: Intl.DateTimeFormatOptions = { month: 'short', day: '2-digit' };
    const startStr = startDate.toLocaleDateString('en-US', options);
    const endStr = endDate.toLocaleDateString('en-US', options);

    return `${startStr} – ${endStr}`;
};

interface Movie {
    title: string;
    year: number;
    bayesian?: number;
    bayesianVoters?: number;
    mubi?: number;
    mubiVoters?: number;
    imdb?: number;
    imdbVoters?: number;
    tmdb?: number;
    tmdbVoters?: number;
    genres: string[];
    duration: number;
    countries: string[];
    directors: string[];
    synopsis: string;
    imageUrl?: string;
    trailerUrl?: string;
}

interface DigestData {
    generatedAt: string;
    totalMovies: number;
    newArrivals: Movie[];
}

const formatRatings = (movie: Movie): string => {
    const parts: string[] = [];
    if (movie.bayesian) parts.push(`⭐ ${movie.bayesian.toFixed(1)}`);
    if (movie.mubi) parts.push(`Mubi: ${movie.mubi.toFixed(1)}`);
    if (movie.imdb) parts.push(`IMDb: ${movie.imdb.toFixed(1)}`);
    if (movie.tmdb) parts.push(`TMDB: ${movie.tmdb.toFixed(1)}`);
    return parts.join(" | ") || "No ratings";
};

export const WeeklyDigestEmail = ({ data = digestData }: { data?: DigestData }) => {
    return (
        <Html>
            <Head />
            <Preview>Kubi Weekly Digest - {data.newArrivals.length} new films this week!</Preview>
            <Tailwind>
                <Body className="bg-gray-100 font-sans">
                    <Container className="mx-auto my-[40px] max-w-[600px] rounded-[8px] bg-white p-0">
                        {/* Header */}
                        <Section className="rounded-t-[8px] bg-[#e91e63] px-[48px] py-[32px] text-center">
                            <Heading className="m-0 text-[28px] font-bold text-white tracking-tight">
                                Kubi Weekly Digest
                            </Heading>
                            <Text className="m-0 mt-[8px] text-[16px] text-gray-200 font-medium">
                                Just Added: {formatDateRange(data.generatedAt)}
                            </Text>
                        </Section>

                        {/* Stats Section */}
                        <Section className="px-[48px] py-[24px]">
                            <table className="w-full">
                                <tbody>
                                    <tr>
                                        <td className="w-1/2 align-top">
                                            <Text className="m-0 text-left text-[18px] leading-[24px] font-bold tracking-tight text-gray-900 tabular-nums">
                                                {data.totalMovies.toLocaleString()}
                                            </Text>
                                            <Text className="m-0 text-left text-[12px] leading-[18px] text-gray-500">
                                                Total Movies
                                            </Text>
                                        </td>
                                        <td className="w-1/2 align-top">
                                            <Text className="m-0 text-left text-[18px] leading-[24px] font-bold tracking-tight text-gray-900 tabular-nums">
                                                {data.newArrivals.length}
                                            </Text>
                                            <Text className="m-0 text-left text-[12px] leading-[18px] text-gray-500">
                                                New This Week
                                            </Text>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </Section>

                        <Hr className="my-[16px] border-gray-300 border-t-2" />




                        <Section className="px-[48px] py-[24px]">
                            {data.newArrivals.map((movie, index) => (
                                <Section key={index} className="my-[16px]">
                                    <Heading as="h2" className="text-left">
                                        {index + 1}. {movie.title} <span className="text-gray-500 font-normal">({movie.year})</span>
                                    </Heading>

                                    <Text className="m-0 mt-[4px] text-[13px] leading-[20px] text-gray-500">
                                        <span className="font-semibold text-gray-900">{movie.genres.join(", ")}</span>
                                        <span className="mx-[8px] text-gray-300">|</span>
                                        {movie.duration} min
                                        {movie.countries.length > 0 && (
                                            <>
                                                <span className="mx-[8px] text-gray-300">|</span>
                                                {movie.countries.join(", ")}
                                            </>
                                        )}
                                    </Text>

                                    {movie.directors.length > 0 && (
                                        <Text className="m-0 mt-[4px] text-[13px] text-gray-500">
                                            Director <span className="font-semibold text-gray-900">{movie.directors.join(", ")}</span>
                                        </Text>
                                    )}

                                    {movie.imageUrl && (
                                        <Img
                                            alt={movie.title}
                                            className="mt-[12px] w-full rounded-[8px] object-cover"
                                            height={280}
                                            src={movie.imageUrl}
                                        />
                                    )}

                                    <table className="w-full mt-[12px]">
                                        <tbody>
                                            <tr>
                                                {(movie.bayesian && movie.bayesian > 0) ? (
                                                    <td className="w-1/4 align-top">
                                                        <Text className="m-0 text-left text-[18px] leading-[24px] font-bold tracking-tight text-gray-900 tabular-nums">
                                                            {movie.bayesian.toFixed(1)} {movie.bayesianVoters ? <span className="text-[14px] font-normal text-gray-400">({formatVoters(movie.bayesianVoters)})</span> : null}
                                                        </Text>
                                                        <Text className="m-0 text-left text-[12px] leading-[18px] text-gray-500">
                                                            Composite
                                                        </Text>
                                                    </td>
                                                ) : null}
                                                {(movie.mubi && movie.mubi > 0) ? (
                                                    <td className="w-1/4 align-top">
                                                        <Text className="m-0 text-left text-[18px] leading-[24px] font-bold tracking-tight text-gray-900 tabular-nums">
                                                            {movie.mubi.toFixed(1)} {movie.mubiVoters ? <span className="text-[14px] font-normal text-gray-400">({formatVoters(movie.mubiVoters)})</span> : null}
                                                        </Text>
                                                        <Text className="m-0 text-left text-[12px] leading-[18px] text-gray-500">
                                                            Mubi
                                                        </Text>
                                                    </td>
                                                ) : null}
                                                {(movie.imdb && movie.imdb > 0) ? (
                                                    <td className="w-1/4 align-top">
                                                        <Text className="m-0 text-left text-[18px] leading-[24px] font-bold tracking-tight text-gray-900 tabular-nums">
                                                            {movie.imdb.toFixed(1)} {movie.imdbVoters ? <span className="text-[14px] font-normal text-gray-400">({formatVoters(movie.imdbVoters)})</span> : null}
                                                        </Text>
                                                        <Text className="m-0 text-left text-[12px] leading-[18px] text-gray-500">
                                                            IMDb
                                                        </Text>
                                                    </td>
                                                ) : null}
                                                {(movie.tmdb && movie.tmdb > 0) ? (
                                                    <td className="w-1/4 align-top">
                                                        <Text className="m-0 text-left text-[18px] leading-[24px] font-bold tracking-tight text-gray-900 tabular-nums">
                                                            {movie.tmdb.toFixed(1)} {movie.tmdbVoters ? <span className="text-[14px] font-normal text-gray-400">({formatVoters(movie.tmdbVoters)})</span> : null}
                                                        </Text>
                                                        <Text className="m-0 text-left text-[12px] leading-[18px] text-gray-500">
                                                            TMDB
                                                        </Text>
                                                    </td>
                                                ) : null}
                                                {(!movie.bayesian && !movie.mubi && !movie.imdb && !movie.tmdb) && (
                                                    <td className="align-top">
                                                        <Text className="m-0 text-left text-[14px] text-gray-500 italic">
                                                            No ratings available
                                                        </Text>
                                                    </td>
                                                )}
                                            </tr>
                                        </tbody>
                                    </table>

                                    <Text className="m-0 mt-[8px] text-[14px] leading-[22px] text-gray-600">
                                        {movie.synopsis}
                                    </Text>

                                    {movie.trailerUrl && (
                                        <Button
                                            className="mt-[12px] rounded-[8px] bg-[#e91e63] px-[16px] py-[10px] text-center text-[14px] font-semibold text-white"
                                            href={movie.trailerUrl}
                                        >
                                            Watch Trailer
                                        </Button>
                                    )}


                                </Section>
                            ))}
                        </Section>

                        {/* Footer */}
                        <Section className="rounded-b-[8px] bg-gray-50 px-[48px] py-[24px] text-center">
                            <Text className="m-0 text-[12px] text-gray-400">
                                This digest was generated automatically from the Mubi catalog.
                            </Text>
                        </Section>
                    </Container>
                </Body>
            </Tailwind>
        </Html >
    );
};

export default WeeklyDigestEmail;
