import { useParams } from 'react-router-dom';
import ReportPage from '../components/local-reports/ReportPage';

export default function LocalReport() {
  const { cbsaSlug } = useParams<{ cbsaSlug: string }>();
  return <ReportPage cbsaSlug={cbsaSlug ?? ''} />;
}
