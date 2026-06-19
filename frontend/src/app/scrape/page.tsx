"use client";

import { useState } from 'react';
import {
  Container,
  Title,
  TextInput,
  Button,
  Table,
  Group,
  Stack,
  Alert,
  Loader,
  Text,
  Skeleton,
} from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';

interface ScrapedProduct {
  title: string | null;
  sku: string | null;
  price: number | null;
  image_url: string | null;
  source_url: string;
}

export default function ScrapePage() {
  const [url, setUrl] = useState('');
  const [selector, setSelector] = useState('');
  const [results, setResults] = useState<ScrapedProduct[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleScrape = async () => {
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch('/api/v1/scrape/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, selector }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to scrape URL.');
      }

      const data: ScrapedProduct[] = await response.json();
      setResults(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const rows = results?.map((product, index) => (
    <Table.Tr key={index}>
      <Table.Td>{product.title || 'N/A'}</Table.Td>
      <Table.Td>{product.sku || 'N/A'}</Table.Td>
      <Table.Td>{product.price !== null ? product.price.toFixed(2) : 'N/A'}</Table.Td>
      <Table.Td>
        {product.image_url ? (
          <img src={product.image_url} alt={product.title || 'Product Image'} width={50} height={50} style={{ objectFit: 'contain' }} />
        ) : (
          'N/A'
        )}
      </Table.Td>
      <Table.Td>{product.source_url}</Table.Td>
    </Table.Tr>
  ));

  return (
    <Container size="xl" py="xl">
      <Stack gap="xl">
        <Title order={1}>Web Scraper</Title>
        <Text c="dimmed">
          Εισάγετε ένα URL και έναν CSS selector για να εξάγετε δεδομένα προϊόντων.
          Ο selector πρέπει να στοχεύει τα containers των προϊόντων.
        </Text>

        <Group align="flex-end">
          <TextInput
            label="URL to Scrape"
            placeholder="e.g., https://example.com/products"
            value={url}
            onChange={(event) => setUrl(event.currentTarget.value)}
            style={{ flexGrow: 1 }}
            required
          />
          <TextInput
            label="CSS Selector for Products"
            placeholder="e.g., .product-item, div[data-product]"
            value={selector}
            onChange={(event) => setSelector(event.currentTarget.value)}
            style={{ flexGrow: 1 }}
            required
          />
          <Button onClick={handleScrape} loading={loading} disabled={!url || !selector}>
            Scrape Page
          </Button>
        </Group>

        {loading && (
          <Table striped highlightOnHover withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Title</Table.Th>
                <Table.Th>SKU</Table.Th>
                <Table.Th>Price</Table.Th>
                <Table.Th>Image</Table.Th>
                <Table.Th>Source URL</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {[...Array(3)].map((_, index) => (
                <Table.Tr key={index}>
                  <Table.Td><Skeleton height={16} /></Table.Td>
                  <Table.Td><Skeleton height={16} /></Table.Td>
                  <Table.Td><Skeleton height={16} /></Table.Td>
                  <Table.Td><Skeleton height={16} width={50} /></Table.Td>
                  <Table.Td><Skeleton height={16} /></Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}

        {error && (
          <Alert icon={<IconAlertCircle size="1rem" />} title="Scraping Error" color="red">
            {error}
          </Alert>
        )}

        {results && results.length > 0 && (
          <Stack>
            <Title order={2}>Scraping Results ({results.length} items)</Title>
            <Table striped highlightOnHover withTableBorder withColumnBorders>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Title</Table.Th>
                  <Table.Th>SKU</Table.Th>
                  <Table.Th>Price</Table.Th>
                  <Table.Th>Image</Table.Th>
                  <Table.Th>Source URL</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>{rows}</Table.Tbody>
            </Table>
          </Stack>
        )}

        {results && results.length === 0 && !loading && !error && (
          <Alert color="blue" title="No Results">
            No products found with the given selector.
          </Alert>
        )}
      </Stack>
    </Container>
  );
}
